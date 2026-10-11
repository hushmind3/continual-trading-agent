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
from .system_operations import system
from ..framework import policy_checkpoint,CASH_ENVIRONMENT,champion_structure_environment

class OperationsRuntime:
    def __init__(self):
        self.lock=threading.RLock()
        self.controls={'feed':False,'paper':False,'engine':False,'learning':False}
        self.learning_pending=[];self.learning_job=None
        self.collector=None;self.thread=None
        self.account=None;self.quotes={};self.decisions=[];self.last_policy_date=None
        self.status={'status':'stopped','error':None}
        self.policy_models={}
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
                'pool':system.expert_pool.catalog() if system.expert_pool else [],
                'settings':read_json(ROOT/'configs/local/operations.json'),
                'policies':{currency:{'path':path,'loaded':self.policy_models.get(currency,{}).get('path')==path,
                    **{key:value for key,value in self.policy_models.get(currency,{}).items() if key not in ('model','path','signature')}}
                    for currency,path in read_json(ROOT/'runtime/operations/policies.json').items()}}

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
                if name=='learning':
                    self.status['learning_status']='완료 시세 대기' if enabled else '중지'
                    if not enabled:
                        self.learning_pending.clear()
                        from .. import web_api as api
                        job=api.job_state()
                        if job.get('running') and job.get('id')==self.learning_job:api.stop()
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
            if self.controls['learning']:self.queue_learning(symbols)

    def queue_learning(self,symbols):
        from .. import web_api as api
        from ..framework import policy_files
        policies=read_json(ROOT/'runtime/operations/policies.json')
        if not policies:
            self.status['learning_error']='운영 모델을 선택·로드한 뒤 지속학습을 켜세요.';return
        for currency,path in policies.items():
            identity=read_json((ROOT/'runtime/official'/path).parent/'dataset.json')
            if set(identity.get('symbols',[]))&set(symbols) and currency not in self.learning_pending:self.learning_pending.append(currency)
        if api.job_state()['running'] or not self.learning_pending:return
        currency=self.learning_pending.pop(0)
        try:
            identity=read_json(policy_files(currency)/'dataset.json')
            request=api.RunRequest(currency=currency,symbols=identity['symbols'],algorithm=identity.get('algorithm','sac'),resume=not bool(identity.get('champion_file')),champion_path=identity.get('champion_file'))
            result=api.launch('train',request,preserve_output=True)
            self.learning_job=result['job']['id']
            self.status.update(learning_status=identity.get('algorithm','sac').upper()+' 이어 학습 실행',learning_job=self.learning_job)
            self.status.pop('learning_error',None)
        except Exception as exc:self.status.update(learning_status='학습 요청 실패',learning_error=str(exc))

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
        catalog=read_json(ROOT/'configs/experts.json')
        # Test status updates do not change the loaded Expert weights or selection.
        signature=json.dumps({'active':catalog.get('active',[]),
            'packages':{key:item.get('package') for key,item in catalog.get('experts',{}).items()}},sort_keys=True)
        if system.expert_pool and signature!=system.expert_pool_signature:
            system.expert_pool.refresh_catalog(catalog);system.expert_pool_signature=signature
        if system.expert_pool is None:
            cfg=settings();cfg.state_dir=ROOT/'runtime/experts'
            system.expert_pool=ExpertPool(cfg,keep_device=True,live=True);system.expert_pool_signature=signature
            system.expert_pool.cancelled=self.cancel_inference.is_set
        return system.expert_pool

    def load(self,key):
        with self.lock:
            pool=self.expert_pool();pool.residency.preload([key])
            metrics=pool.metrics.get(key,{})
            if not metrics.get('preloaded'):raise ValueError(metrics.get('error','Expert를 적재하지 못했습니다.'))
            metrics.pop('error',None)
            return metrics

    def unload(self,key):
        with self.lock:
            if system.expert_pool and key in system.expert_pool.loaded:system.expert_pool.release(key)

    def fixture(self,key,*,frame=None,account=None,all_batches=False):
        from .expert_inference import prepare_inputs
        with self.lock:entry=self.expert_pool().entries[key]
        if frame is None:frame=prices('USD')
        if frame.empty:raise ValueError('실제 USD 가격 데이터가 없습니다.')
        if account is None:
            book=self.ledger().snapshot()['books']['USD']
            account={'currency':'USD','cash':book['cash'],'nav':book['equity'],
                     'positions':{symbol:position['quantity'] for symbol,position in book['positions'].items()}}
        snapshot,batches=prepare_inputs(entry,frame,account)
        return {'input':batches[0],'inputs':batches if all_batches else batches[:1],'snapshot':snapshot}

    def infer(self,key,fixture=None):
        self.inference_active+=1
        try:return self._infer(key,fixture)
        finally:self.inference_active-=1

    def _infer(self,key,fixture=None):
        from .expert_inference import run_batches
        fixture=fixture or self.fixture(key,all_batches=True)
        with self.lock:
            pool=self.expert_pool()
            packets=run_batches(pool,key,fixture['snapshot'],fixture.get('inputs',[fixture['input']]))
            values=np.concatenate([np.asarray(packet['native_output'],dtype=float).reshape(-1) for packet in packets])
            symbols_checked=sum(len(packet['symbols']) for packet in packets)
            report=read_json(ROOT/'runtime/experts/status.json')
            report.setdefault('experts',{})[key]={'status':'ready','as_of':fixture['snapshot']['as_of'],
                'output':values.tolist(),'batches':len(packets),'symbols_checked':symbols_checked}
            report.update(as_of=fixture['snapshot']['as_of'],resources=pool.metrics)
            atomic_json(report,ROOT/'runtime/experts/status.json')
            return {'packet':packets[0],'packets':packets,'metrics':dict(pool.metrics.get(key,{})),
                'batches':len(packets),'symbols_checked':symbols_checked}

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

    def check_policy(self,files,*,load=False):
        self.inference_active+=1
        try:
            with self.lock:return self._check_policy(files,load=load)
        finally:self.inference_active-=1

    def _check_policy(self,files,*,load=False):
        identity=read_json(files/'dataset.json')
        champion_ids=identity.get('champion_experts',[])
        registry=system.expert_registry(files,self.expert_pool)
        if identity.get('environment')!=CASH_ENVIRONMENT:raise ValueError('PortfolioOptimizationEnv 정책이 필요합니다. 구형 정책을 실행하지 않습니다.')
        env=champion_structure_environment(identity['currency'],identity['symbols'],registry,champion_ids)
        try:
            model=system.model(policy_checkpoint(files),identity.get('algorithm','sac'),env)
            info={'path':policy_checkpoint(files).relative_to(ROOT/'runtime/official').as_posix(),'algorithm':identity.get('algorithm','sac'),'device':str(model.device),
                'observation_shape':list(model.observation_space.shape),'action_shape':list(model.action_space.shape),
                'num_timesteps':int(model.num_timesteps),'updates':int(getattr(model,'_n_updates',0))}
            if load:
                file=policy_checkpoint(files);stat=file.stat()
                self.policy_models[identity['currency']]={**info,'signature':(stat.st_mtime_ns,stat.st_size)}
                self.last_policy_date=None
            return info
        finally:env.close()

    def _sac_decision(self,files):
        identity=read_json(files/'dataset.json')
        cash_enabled=identity.get('environment')==CASH_ENVIRONMENT
        if identity.get('environment')!=CASH_ENVIRONMENT:
            raise ValueError('현재 저장 SAC는 기존 환경의 파일입니다. 현재 원본 환경으로 학습한 정책이 필요합니다.')
        symbols=identity['symbols'];currency=identity['currency'];frame=prices(currency,symbols)
        registry=system.expert_registry(files,self.expert_pool);champion_ids=identity.get('champion_experts',[])
        prepared=training_environment(frame,registry,training=False,champion_ids=champion_ids)
        latest=prepared.unwrapped.gym_env
        latest._time_index=len(latest._sorted_times)-1
        latest._state,latest._info=latest._get_state_and_info_from_time_index(latest._time_index)
        wrapped=prepared
        try:
            file=policy_checkpoint(files);stat=file.stat();path=file.relative_to(ROOT/'runtime/official').as_posix()
            model=system.model(file,identity.get('algorithm','sac'),wrapped)
            self.policy_models[currency]={'path':path,'algorithm':identity.get('algorithm','sac'),'signature':(stat.st_mtime_ns,stat.st_size),
                'device':str(model.device),'observation_shape':list(model.observation_space.shape),'action_shape':list(model.action_space.shape),
                'num_timesteps':int(model.num_timesteps),'updates':int(getattr(model,'_n_updates',0))}
            book=self.ledger().snapshot()['books'][currency]
            wrapped.live_account={'currency':currency,'nav':book['equity'],'cash':book['cash'],
                'positions':{symbol:row['quantity'] for symbol,row in book['positions'].items()}}
            observation=wrapped.observation(latest._state)
            action,_=model.predict(observation,deterministic=True)
            import math
            allocation=action if math.isclose(float(np.sum(action)),1,abs_tol=1e-6) and np.min(action)>=0 else latest._softmax_normalization(action)
            weights=allocation[1:];cash_weight=float(allocation[0])
            bars=frame[frame.date==frame.date.max()].set_index('symbol')
            stamp=str(bars.date.iloc[0])
            panel=SimpleNamespace(dates=[stamp],symbols=symbols,groups={
                s:('KRX' if s.endswith('.KS') else 'KOSDAQ' if s.endswith('.KQ') else 'US','equity') for s in symbols},
                observed=np.ones((1,len(symbols)),dtype=bool),closes=np.array([[float(bars.loc[s,'close']) for s in symbols]]),
                features=np.zeros((1,len(symbols),8)))
            with self.lock:
                book=self.ledger().snapshot()['books'][currency];nav=book['equity']
                current=[book['positions'].get(s,{}).get('quantity',0)*float(bars.loc[s,'close'])/nav if nav else 0 for s in symbols]
                actions=np.array([2 if weight>held else 0 if weight<held else 1 for weight,held in zip(weights,current)])
                self.ledger().queue_decisions(panel,0,np.tile([0.,1.,0.],(len(symbols),1)),self.controls['paper'],
                    allocation=[*weights,cash_weight],actions=actions)
                self.ledger().save()
                self.decisions.extend({'symbol':s,'currency':currency,'target_weight':float(weight),'as_of':stamp} for s,weight in zip(symbols,weights))
                self.decisions.append({'symbol':'CASH','currency':currency,'target_weight':cash_weight,'as_of':stamp,'cash_action':cash_enabled})
                self.status.pop('policy_error',None)
        finally:
            wrapped.close()
            if wrapped is not prepared:prepared.close()

    def close(self):
        self.command('feed',False)
        if system.expert_pool:system.expert_pool.close()

runtime=OperationsRuntime()
