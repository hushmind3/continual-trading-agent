"""Connect recovered account/feed/Expert modules to the current native SAC path."""
from __future__ import annotations
import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
from ..framework import ROOT,prices,training_environment
from ..state_io import read_json,atomic_json
from ..paper_account import PaperAccount
from .operations_settings import settings

class OperationsRuntime:
    def __init__(self):
        self.lock=threading.RLock()
        self.controls={'feed':False,'paper':False,'engine':False}
        self.collector=None;self.thread=None;self.pool=None;self.pool_signature=None
        self.account=None;self.quotes={};self.decisions=[];self.last_policy_date=None
        self.status={'status':'stopped','error':None}
        self.feed_cycle=threading.Event();self.cancel_inference=threading.Event();self.inference_active=0

    def ledger(self):
        cfg=settings()
        if self.account is None:self.account=PaperAccount(cfg.state_dir/'paper-account.json',cfg.risk.fee,cfg.risk.slippage)
        return self.account

    def snapshot(self):
        with self.lock:
            account=self.ledger().snapshot()
            return {'controls':self.controls.copy(),'account':account,'quotes':self.quotes.copy(),
                'decisions':self.decisions,'feed':dict(self.status),
                'broker':dict(self.collector.broker_status) if self.collector else {},
                'pool':self.pool.catalog() if self.pool else [],
                'settings':read_json(ROOT/'configs/local/operations.json')}

    def command(self,name,enabled):
        with self.lock:
            if name not in self.controls:raise ValueError('feed / paper / engine 제어를 선택하세요.')
            if name=='feed':
                if enabled and not self.controls['feed']:
                    if self.thread and self.thread.is_alive():raise ValueError('이전 시세 수신 작업이 종료 중입니다.')
                    self.feed_cycle.clear()
                    self.controls['feed']=True
                    self.status={'status':'starting','error':None}
                    self.thread=threading.Thread(target=self.run,name='market-paper',daemon=True)
                    self.thread.start()
                elif not enabled:
                    self.controls['feed']=False
                    if self.collector:
                        self.collector.stop.set();self.collector.broker_stop.set()
            else:
                if name=='engine' and enabled:self.cancel_inference.clear()
                self.controls[name]=bool(enabled)
            return self.controls.copy()

    def run(self):
        collector=None
        try:
            from ..live_feed import LiveMarketCollector
            cfg=settings();source=read_json(ROOT/'configs/instruments.json')
            if cfg.symbols:source['instruments']=[i for i in source['instruments'] if i['symbol'] in cfg.symbols]
            config=cfg.state_dir/'live-symbols.json';atomic_json(source,config)
            collector=LiveMarketCollector(config,cfg.state_dir/'live/market.csv',
                poll_seconds=cfg.data.poll_seconds,timeout=cfg.data.timeout_seconds)
            with self.lock:self.collector=collector
            # Existing writer persists incoming bars through the official DataStore.
            original_append=collector.index.append
            def append(rows):
                added=original_append(rows)
                if rows:self.status.update(last_received_at=time.time(),last_as_of=str(max(row['date'] for row in rows)))
                if added:self.accept(rows)
                return added
            collector.index.append=append
            original_collect=collector.collect_once
            def collect_once():
                try:return original_collect()
                finally:self.feed_cycle.set()
            collector.collect_once=collect_once
            if collector.broker_provider=='kiwoom':
                from .kiwoom_data import BrokerStreams
                broker=BrokerStreams(collector);broker.start();collector.broker_thread=broker.thread
            else:broker=None
            try:
                self.status={'status':'running','error':None}
                collector.run()
            finally:
                if broker:broker.close()
        except Exception as exc:
            self.status={'status':'failed','error':str(exc)}
        finally:
            with self.lock:
                self.controls['feed']=False;self.collector=None
                if self.status.get('status')!='failed':self.status['status']='stopped'

    def accept(self,rows):
        frame=pd.DataFrame(rows)
        if frame.empty:return
        for stamp,group in frame.sort_values('date').groupby('date',sort=True):
            records=group.to_dict('records');symbols=[r['symbol'] for r in records]
            features=np.zeros((1,len(records),8),dtype=float)
            for index,row in enumerate(records):
                bid,ask=row.get('bid'),row.get('ask')
                if bid and ask:features[0,index,7]=(float(ask)-float(bid))/float(row['close'])*10000
            panel=SimpleNamespace(dates=[str(stamp)],symbols=symbols,
                groups={r['symbol']:(r['market'],r['asset_class']) for r in records},
                observed=np.ones((1,len(records)),dtype=bool),
                closes=np.array([[float(r['close']) for r in records]]),features=features)
            with self.lock:
                self.quotes.update({r['symbol']:r for r in records})
                self.ledger().process_bar(panel,0,self.controls['paper'])
                self.ledger().save()
                self.status.update(last_as_of=str(stamp),received_symbols=len(self.quotes))
            if self.controls['engine'] and self.last_policy_date!=str(stamp):
                try:self.sac_decision()
                except Exception as exc:self.status['policy_error']=str(exc)
                self.last_policy_date=str(stamp)

    def manual_order(self,symbol,currency,action,quantity):
        from ..paper_account import _currency
        items=read_json(ROOT/'configs/instruments.json').get('instruments',[])
        item=next((i for i in items if i['symbol']==symbol),None)
        if not item or _currency(item['market'],item['asset_class'])!=currency:raise ValueError('계좌 통화에 맞는 등록 종목을 선택하세요.')
        with self.lock:
            row=self.quotes.get(symbol)
            source='live'
            if not row:
                frame=prices(currency,[symbol])
                if frame.empty:raise ValueError('실제 저장 가격이나 수신 시세가 없습니다.')
                row=frame.sort_values('date').iloc[-1].to_dict();source='stored'
            price=float(row['close']);bid=row.get('bid');ask=row.get('ask')
            spread=(float(ask)-float(bid))/price if bid and ask else 0
            fill=self.ledger()._fill(symbol,currency,action,price,spread,
                float(quantity) if action=='SELL' else price*quantity,
                str(row['date']),requested_quantity=quantity if action=='BUY' else None)
            if fill is None:raise ValueError('현재 현금 또는 보유 수량으로 체결할 수 없는 주문입니다.')
            self.ledger().state['books'][currency]['marks'][symbol]=price
            self.ledger().save()
            return {'fill':fill,'price_source':source,'quote_as_of':str(row['date'])}

    def expert_pool(self):
        from .assets import ExpertPool
        signature=json.dumps(read_json(ROOT/'configs/experts.json'),sort_keys=True)
        if self.pool and signature!=self.pool_signature:self.pool.close();self.pool=None
        if self.pool is None:
            cfg=settings();cfg.state_dir=ROOT/'runtime/experts'
            self.pool=ExpertPool(cfg,keep_device=True,live=True);self.pool_signature=signature
            self.pool.cancelled=self.cancel_inference.is_set
        return self.pool

    def load(self,key):
        with self.lock:
            pool=self.expert_pool();pool.residency.preload([key])
            metrics=pool.metrics.get(key,{})
            if not metrics.get('preloaded'):raise ValueError(metrics.get('error','Expert를 적재하지 못했습니다.'))
            metrics.pop('error',None)
            return metrics

    def unload(self,key):
        with self.lock:
            if self.pool and key in self.pool.loaded:self.pool.release(key)

    def fixture(self,key):
        from .expert_packages import load_package
        from .observations import native_input
        cfg=settings();catalog=read_json(cfg.registry_file);item=catalog['experts'][key]
        package=load_package(Path(cfg.expert_checkpoint),item['package'],verify=True)
        currency='USD'
        frame=prices(currency)
        if frame.empty:raise ValueError('실제 USD 가격 데이터가 없습니다.')
        frame=frame.sort_values('date');stamp=frame.date.max()
        daily=frame[frame.date<pd.Timestamp(stamp).normalize()]
        book=self.ledger().snapshot()['books'][currency]
        snapshot={'symbols':sorted(frame.symbol.unique()),'as_of':str(stamp),
            'stock_policy_history':daily.assign(date=daily.date.astype(str)).to_dict('records'),
            'policy_account':{'currency':currency,'cash':book['cash'],'nav':book['equity'],
                'positions':{s:p['quantity'] for s,p in book['positions'].items()}}}
        batches=[None] if package['entry'].get('stock_policy') else native_input(package['entry']['backend'],frame,daily,str(stamp))
        return {'input':batches[0],'snapshot':snapshot}

    def infer(self,key,fixture=None):
        self.inference_active+=1
        try:return self._infer(key,fixture)
        finally:self.inference_active-=1

    def _infer(self,key,fixture=None):
        fixture=fixture or self.fixture(key)
        with self.lock:
            pool=self.expert_pool();packet=pool.run(key,fixture['input'],fixture['snapshot'])
            values=np.asarray(packet['native_output'],dtype=float)
            if not np.isfinite(values).all():raise ValueError('Expert 출력에 NaN/Inf가 있습니다.')
            packet['native_output']=values.tolist()
            report=read_json(ROOT/'runtime/experts/status.json')
            report.setdefault('experts',{})[key]={'status':'ready','as_of':fixture['snapshot']['as_of'],'output':values.reshape(-1).tolist()}
            report.update(as_of=fixture['snapshot']['as_of'],resources=pool.metrics)
            atomic_json(report,ROOT/'runtime/experts/status.json')
            return {'packet':packet,'metrics':dict(pool.metrics.get(key,{}))}

    def sac_decision(self):
        from ..framework import policy_files
        self.inference_active+=1
        try:
            selected=read_json(ROOT/'runtime/operations/policies.json')
            files=[(ROOT/'runtime/official'/path).resolve().parent for path in selected.values()] if selected else [policy_files()]
            with self.lock:
                self.decisions=[]
                for folder in files:
                    if not folder.is_relative_to((ROOT/'runtime/official').resolve()):raise ValueError('운영 정책 경로가 runtime/official 밖에 있습니다.')
                    if self.cancel_inference.is_set() or not self.controls['engine']:break
                    self._sac_decision(folder)
        finally:self.inference_active-=1

    def check_policy(self,files):
        self.inference_active+=1
        try:return self._check_policy(files)
        finally:self.inference_active-=1

    def _check_policy(self,files):
        from stable_baselines3 import SAC
        from ..expert_registry_native import ExpertRegistry
        identity=read_json(files/'dataset.json')
        env=training_environment(prices(identity['currency'],identity['symbols']),ExpertRegistry(self.expert_pool),training=False)
        try:SAC.load(files/'sac.zip',env=env)
        finally:env.close()

    def _sac_decision(self,files):
        from stable_baselines3 import SAC
        from ..expert_registry_native import ExpertRegistry
        from ..expert_observation import ExpertObservation
        identity=read_json(files/'dataset.json')
        if identity.get('environment')!='finrl.meta.env_portfolio_allocation.env_portfolio.StockPortfolioEnv':
            raise ValueError('현재 저장 SAC는 기존 환경의 파일입니다. 현재 원본 환경으로 학습한 정책이 필요합니다.')
        symbols=identity['symbols'];currency=identity['currency'];frame=prices(currency,symbols)
        prepared=training_environment(frame,ExpertRegistry(self.expert_pool),training=False)
        raw=prepared.unwrapped
        # Use the official day constructor for latest-state inference, with identical environment arguments.
        latest=raw.__class__(df=raw.df,stock_dim=raw.stock_dim,hmax=raw.hmax,initial_amount=raw.initial_amount,
            transaction_cost_pct=raw.transaction_cost_pct,reward_scaling=raw.reward_scaling,
            state_space=raw.state_space,action_space=raw.stock_dim,tech_indicator_list=raw.tech_indicator_list,
            day=int(raw.df.index.max()))
        wrapped=ExpertObservation(latest,prepared.registry,frame,symbols);wrapped.currency=currency
        try:
            model=SAC.load(files/'sac.zip',env=wrapped)
            observation=wrapped.observation(latest.state)
            action,_=model.predict(observation,deterministic=True)
            weights=latest.softmax_normalization(action)
            bars=latest.data.set_index('tic');stamp=str(bars.date.iloc[0])
            panel=SimpleNamespace(dates=[stamp],symbols=symbols,groups={
                s:('KRX' if s.endswith('.KS') else 'KOSDAQ' if s.endswith('.KQ') else 'US','equity') for s in symbols},
                observed=np.ones((1,len(symbols)),dtype=bool),closes=np.array([[float(bars.loc[s,'close']) for s in symbols]]),
                features=np.zeros((1,len(symbols),8)))
            with self.lock:
                book=self.ledger().snapshot()['books'][currency];nav=book['equity']
                current=[book['positions'].get(s,{}).get('quantity',0)*float(bars.loc[s,'close'])/nav if nav else 0 for s in symbols]
                actions=np.array([2 if weight>held else 0 if weight<held else 1 for weight,held in zip(weights,current)])
                self.ledger().queue_decisions(panel,0,np.tile([0.,1.,0.],(len(symbols),1)),self.controls['paper'],
                    allocation=[*weights,0.],actions=actions)
                self.ledger().save()
                self.decisions.extend({'symbol':s,'currency':currency,'target_weight':float(weight),'as_of':stamp} for s,weight in zip(symbols,weights))
                self.status.pop('policy_error',None)
        finally:
            wrapped.close();prepared.close()

    def close(self):
        self.command('feed',False)
        if self.pool:self.pool.close()

runtime=OperationsRuntime()
