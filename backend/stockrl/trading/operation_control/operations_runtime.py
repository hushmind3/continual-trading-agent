"""Connect recovered account/feed/Expert modules to the current native SAC path."""
from __future__ import annotations
from stockrl.expert_registry import read_catalog
import json
import threading
import time
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
from stockrl import ROOT
from stockrl.finrl.price_data.operations import prices
from stockrl.finrl.framework import training_environment
from stockrl.state_io import read_json
from stockrl.state_io import atomic_json
from stockrl.state_io import update_json
from stockrl.trading.virtual_account_orders.paper_account import PaperAccount
from stockrl.trading.virtual_account_orders.paper_account import _moment
from stockrl.trading.operation_control.operations_settings import settings
from stockrl.platform.system_operations import system
from stockrl.finrl.framework import policy_checkpoint
from stockrl.finrl.framework import CASH_ENVIRONMENT
from stockrl.finrl.framework import policy_timeframe
from stockrl.finrl.framework import champion_structure_environment


def learning_budget(identity,pending_observations,poll_seconds):
    """Schedule work; preserve official algorithm parameters and rollout units."""
    import math
    from stockrl.finrl.framework import sac_example
    _,parameters,limit=sac_example(identity.get('algorithm','sac'))
    limit=max(1,int(limit));minimum=min(limit,max(1,int(parameters.get('n_steps',1))))
    target=float(poll_seconds)
    if not math.isfinite(target) or target<=0:raise ValueError('학습 작업 시간 기준이 유효하지 않습니다.')
    desired=min(limit,max(minimum,int(pending_observations)))
    previous=identity.get('training_input',{});elapsed=previous.get('elapsed_seconds');transitions=previous.get('transitions')
    rate=None;capacity=None
    if elapsed is not None and transitions is not None:
        elapsed=float(elapsed);transitions=int(transitions)
        if not math.isfinite(elapsed) or elapsed<=0 or transitions<1:raise ValueError('저장된 학습 속도 기록이 유효하지 않습니다.')
        rate=transitions/elapsed;capacity=max(1,int(target*rate))
        desired=min(desired,max(minimum,capacity))
    return {'requested_timesteps':desired,'target_seconds':target,
        'estimated_seconds':desired/rate if rate else None,'rollout_minimum':minimum,
        'rollout_exceeds_target':capacity is not None and minimum>capacity}


class OperationsRuntime:
    def __init__(self):
        self.lock=threading.RLock()
        self.controls={'feed':False,'paper':False,'engine':False,'learning':False}
        self.learning_pending=[];self.learning_job=None;self.learning_versions={};self.learning_context=None;self.learning_version_sources={};self.learning_scheduling=threading.Lock()
        self.collector=None;self.thread=None;self.policy_thread=None
        self.account=None;self.quotes={};self.decisions=[];self.last_policy_dates={}
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
            resident={row['path'] for row in system.resident_models()}
            return {'controls':self.controls.copy(),'account':account,'quotes':self.quotes.copy(),
                'decisions':self.decisions,'feed':dict(self.status),
                'broker':dict(self.collector.broker_status) if self.collector else {},
                'pool':system.expert_pool.catalog() if system.expert_pool else [],
                'learning':{'current':dict(self.learning_context) if self.learning_context else None,'pending':list(self.learning_pending),'versions':dict(self.learning_versions),'status':self.status.get('learning_status','지속학습 대기'),'error':self.status.get('learning_error'),'last_completed':self.status.get('learning_completed'),'last_applied':self.status.get('learning_applied')},
                'settings':read_json(ROOT/'configs/local/operations.json'),
                'policies':{currency:{'path':path,'loaded':self.policy_models.get(currency,{}).get('path')==path and str((ROOT/'runtime/official'/path).resolve()) in resident,
                    **{key:value for key,value in self.policy_models.get(currency,{}).items() if key not in ('model','path','signature')}}
                    for currency,path in read_json(ROOT/'runtime/operations/policies.json').items()}}

    def command(self,name,enabled):
        if name=='engine' and not enabled:self.cancel_inference.set()
        with self.lock:
            if name not in self.controls:raise ValueError('feed / paper / engine 제어를 선택하세요.')
            if name in ('engine','learning') and enabled:
                policies=read_json(ROOT/'runtime/operations/policies.json')
                if not policies:raise ValueError('운영 정책을 모델 선택 화면에서 직접 승인하세요.')
                for currency,path in policies.items():
                    checkpoint=(ROOT/'runtime/official'/path).resolve()
                    if not checkpoint.is_relative_to((ROOT/'runtime/official').resolve()):raise ValueError('승인 정책 경로가 운영 폴더 밖입니다.')
                    identity=read_json(checkpoint.parent/'dataset.json')
                    if identity.get('currency')!=currency:raise ValueError(f"{currency} 운영에 {identity.get('currency','통화 미기록')} 모델이 선택되어 있습니다. 정책 학습 화면에서 해당 모델을 다시 로드하세요.")
                    if policy_checkpoint(checkpoint.parent)!=checkpoint:raise ValueError('승인 정책 경로가 저장된 알고리즘과 다릅니다.')
                    self._check_policy(checkpoint.parent,load=True)
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

            result=self.controls.copy()
        if name=='learning' and not enabled:
            with system.job_lock:
                job=system.job_state()
                if job.get('running') and job.get('id')==self.learning_job:system.stop_job()
        return result

    def run(self):
        collector=None
        try:
            from stockrl.live_feed import LiveMarketCollector
            cfg=settings();source=read_json(ROOT/'configs/instruments.json')
            if cfg.symbols:source['instruments']=[i for i in source['instruments'] if i['symbol'] in cfg.symbols]
            config=cfg.state_dir/'live-symbols.json';atomic_json(source,config)
            collector=LiveMarketCollector(config,cfg.state_dir/'live/market.csv',
                poll_seconds=cfg.data.poll_seconds,timeout=cfg.data.timeout_seconds)
            with self.lock:self.collector=collector
            # Raw bars are persisted separately; only accepted rows update the ledger.
            original_append=collector.index.append
            def append(rows):
                added=original_append(rows)
                if rows:self.status.update(last_received_at=time.time(),last_as_of=str(max(row['date'] for row in rows)))
                if added:self.accept(collector.index.last_added_rows)
                return added
            collector.index.append=append
            original_collect=collector.collect_once
            def collect_once():
                try:return original_collect()
                finally:self.feed_cycle.set()
            collector.collect_once=collect_once
            self.policy_thread=threading.Thread(target=self.process_updates,name='policy-updates',daemon=True)
            self.policy_thread.start()
            if collector.broker_provider=='kiwoom':
                from stockrl.platform.kiwoom_data import BrokerStreams
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
            self.feed_cycle.set()

    def accept(self,rows):
        frame=pd.DataFrame(rows)
        if frame.empty:return
        for stamp,group in frame.sort_values('date').groupby('date',sort=True):
            group=group.astype(object).where(group.notna(),None)
            with self.lock:
                records=[r for r in group.to_dict('records') if r['symbol'] not in self.quotes or _moment(r['date'])>_moment(self.quotes[r['symbol']]['date'])]
            if not records:continue
            symbols=[r['symbol'] for r in records]
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
                self.status['received_symbols']=len(self.quotes)
                previous=self.status.get('last_as_of')
                if previous is None or _moment(stamp)>_moment(previous):self.status['last_as_of']=str(stamp)
        self.feed_cycle.set()

    def process_updates(self):
        while self.controls['feed']:
            received=self.feed_cycle.wait(timeout=1 if self.learning_context else None);self.feed_cycle.clear()
            if self.learning_context:
                with self.lock,system.job_lock:received=bool(self.finish_learning()) or received
            if not received:continue
            if not self.controls['feed']:break
            if self.controls['engine']:
                try:self.sac_decision()
                except Exception as exc:
                    with self.lock:self.status['policy_error']=str(exc)
            if self.controls['learning']:
                with self.lock:symbols=list(self.quotes)
                try:self.queue_learning(symbols)
                except Exception as exc:
                    with self.lock:self.status.update(learning_status='학습 입력 오류',learning_error=str(exc))

    def finish_learning(self):
        context=self.learning_context
        if not context:return
        job=system.job_state()
        if job.get('id')!=context['id']:
            record=(ROOT/'runtime/official/jobs'/(context['id']+'.json')).resolve()
            job=read_json(record) if record.is_relative_to((ROOT/'runtime/official/jobs').resolve()) else {}
        if not job or job.get('status') in ('starting','running') or job.get('running'):return
        self.learning_context=None;currency=context['currency']
        if job.get('status')!='succeeded' or job.get('exit_code')!=0:
            self.status.update(learning_status='지속학습 실패 · 같은 입력 재시도 가능',learning_error=job.get('error') or job.get('detail') or '학습 완료 기록을 확인하지 못했습니다.')
            return
        try:
            from stockrl.finrl.policy_learning import handlers as learning
            root=(ROOT/'runtime/official').resolve();folder=(root/context['output']).resolve()
            if not folder.is_relative_to(root):raise ValueError('학습 결과 경로가 운영 폴더 밖입니다.')
            identity=read_json(folder/'dataset.json')
            if policy_timeframe(identity)!=policy_timeframe(context['identity']):raise ValueError('학습 결과의 가격 주기가 기준 정책과 다릅니다.')
            for key in ('currency','algorithm','symbols','environment','champion_experts'):
                if key in context['identity'] and identity.get(key)!=context['identity'][key]:raise ValueError('학습 결과의 '+key+' 계약이 기준 정책과 다릅니다.')
            checked=learning.model_state(learning.source_settings(),folder)
            if not checked['compatible']:raise ValueError('학습 결과를 운영에 반영할 수 없습니다: '+' · '.join(checked['reasons']))
            consumed=identity.get('training_input',{}).get('consumed_end')
            if not consumed:raise ValueError('실제로 학습한 마지막 시각의 기록이 없습니다.')
            stamp=pd.Timestamp(consumed);training_input=identity['training_input']
            if pd.isna(stamp) or stamp>pd.Timestamp(training_input['end']):raise ValueError('학습한 시각이 실제 입력 범위 밖입니다.')
            if int(training_input.get('transitions') or 0)<1:raise ValueError('실제 학습 전이 기록이 없습니다.')
            previous=context['identity'].get('training_input',{}).get('consumed_end')
            if previous and stamp<pd.Timestamp(previous):raise ValueError('학습 완료 시각이 기준 정책보다 이전입니다.')
            if previous and context['input'].get('pending_observations',0)>0 and stamp<=pd.Timestamp(previous):raise ValueError('대기 중인 새 가격을 학습한 기록이 없습니다.')
            checkpoint=policy_checkpoint(folder);relative=checkpoint.relative_to(root).as_posix()
            self.learning_versions[currency]=identity.get('training_input',{}).get('fingerprint',context['version'])
            self.status['learning_completed']={'id':context['id'],'currency':currency,'path':relative,'num_timesteps':checked.get('num_timesteps'),'updates':checked.get('updates'),'at':job.get('finished_at'),
                'consumed_end':consumed,'transitions':identity['training_input'].get('transitions')}
            applied=False
            def select(current):
                nonlocal applied
                if not self.controls['learning'] or current.get(currency)!=context['source']:return None
                source=root/context['source']
                if context.get('source_signature') and (source.stat().st_mtime_ns,source.stat().st_size)!=tuple(context['source_signature']):return None
                applied=True;return {**current,currency:relative}
            update_json(ROOT/'runtime/operations/policies.json',select)
            self.learning_version_sources[currency]=relative if applied else context['source']
            self.status.update(learning_status='학습 완료 · 구조 확인된 새 버전 운영 반영' if applied else '학습 완료 · 기준 정책 변경/학습 중지로 반영 보류')
            if applied:
                self.status['learning_applied']=dict(self.status['learning_completed'])
                self.policy_models.pop(currency,None)
            self.status.pop('learning_error',None)
            return True
        except (ValueError,OSError,KeyError) as error:
            self.status.update(learning_status='학습 결과 검증 실패',learning_error=str(error))

    def queue_learning(self,symbols):
        if not self.learning_scheduling.acquire(blocking=False):return
        try:
            with self.lock,system.job_lock:
                self.finish_learning()
                if not self.controls['learning'] or self.learning_context:return
            from stockrl.finrl.policy_learning import handlers as learning
            policies=read_json(ROOT/'runtime/operations/policies.json')
            if not policies:
                with self.lock:self.status['learning_error']='운영 모델을 선택·로드한 뒤 지속학습을 켜세요.'
                return
            candidates={}
            for currency,path in policies.items():
                identity=read_json((ROOT/'runtime/official'/path).parent/'dataset.json')
                if not set(identity.get('symbols',[]))&set(symbols):continue
                frame=prices(currency,identity['symbols'],timeframe=policy_timeframe(identity))
                if frame.empty:continue
                version=sha256(pd.util.hash_pandas_object(frame,index=True).values.tobytes()).hexdigest()
                consumed=identity.get('training_input',{}).get('consumed_end')
                dates=pd.to_datetime(frame.date)
                pending=int(dates[dates>pd.Timestamp(consumed)].nunique()) if consumed else int(dates.nunique())
                candidates[currency]=(path,identity,version,{'observations':len(frame),'end':str(frame.date.max()),'timeframe':frame.attrs.get('timeframe','미지정'),
                    'consumed_end':consumed,'pending_observations':pending})
            with self.lock,system.job_lock:
                if not self.controls['learning'] or self.learning_context:return
                current=read_json(ROOT/'runtime/operations/policies.json')
                for currency,(path,identity,version,data) in candidates.items():
                    if current.get(currency)!=path:continue
                    if not data['pending_observations']:
                        self.learning_pending=[item for item in self.learning_pending if item!=currency]
                        continue
                    if currency not in self.learning_pending:self.learning_pending.append(currency)
                if system.job_state().get('running') or not self.learning_pending:return
                currency=self.learning_pending.pop(0)
                if currency not in candidates:return
                source,identity,version,data=candidates[currency]
                if current.get(currency)!=source:return
                try:
                    checkpoint=(ROOT/'runtime/official'/source).resolve()
                    if not checkpoint.is_relative_to((ROOT/'runtime/official').resolve()):raise ValueError('기준 정책 경로가 운영 폴더 밖입니다.')
                    stat=checkpoint.stat()
                    data.update(learning_budget(identity,data['pending_observations'],settings().data.poll_seconds))
                    request=learning.RunRequest(currency=currency,algorithm=identity.get('algorithm','sac'),resume=True,champion_path=identity.get('champion_file'),checkpoint=str(checkpoint),timeframe=policy_timeframe(identity),total_timesteps=data['requested_timesteps'])
                    result=learning.launch('train',request,preserve_output=True,continuous=True);job=result['job']
                    self.learning_job=job['id']
                    self.learning_context={'id':job['id'],'currency':currency,'source':source,'source_signature':[stat.st_mtime_ns,stat.st_size],'version':version,'identity':dict(identity),'input':data,'output':job['output']}
                    self.status.update(learning_status=identity.get('algorithm','sac').upper()+' 이어 학습 실행',learning_job=self.learning_job)
                    self.status.pop('learning_error',None)
                except Exception as error:self.status.update(learning_status='학습 요청 실패',learning_error=str(error))
        finally:self.learning_scheduling.release()

    def manual_order(self,symbol,currency,action,quantity):
        from stockrl.trading.virtual_account_orders.paper_account import _currency
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
            from stockrl.live_feed import LIVE_QUOTE_MAX_AGE_SECONDS
            stamp=pd.Timestamp(row['date'])
            if pd.isna(stamp):raise ValueError('시세 시각을 확인할 수 없어 즉시 체결할 수 없습니다.')
            if stamp.tzinfo is None:stamp=stamp.tz_localize('UTC')
            age=(pd.Timestamp.now(tz='UTC')-stamp).total_seconds()
            if age<0 or age>LIVE_QUOTE_MAX_AGE_SECONDS:raise ValueError('유효한 최신 시세가 없어 즉시 체결할 수 없습니다.')
            import math
            try:price=float(row.get('close'))
            except (TypeError,ValueError) as exc:raise ValueError('유효한 시세 가격이 없습니다.') from exc
            if not math.isfinite(price) or price<=0:raise ValueError('시세 가격은 유한한 양수여야 합니다.')
            bid=row.get('bid');ask=row.get('ask');spread=0
            if bid is not None and ask is not None:
                try:bid=float(bid);ask=float(ask)
                except (TypeError,ValueError) as exc:raise ValueError('호가 가격을 확인할 수 없습니다.') from exc
                if not all(math.isfinite(value) and value>0 for value in (bid,ask)) or ask<bid:
                    raise ValueError('유효한 매수·매도 호가가 없습니다.')
                spread=(ask-bid)/price
            fill=self.ledger()._fill(symbol,currency,action,price,spread,
                float(quantity) if action=='SELL' else price*quantity,
                str(row['date']),requested_quantity=quantity if action=='BUY' else None)
            if fill is None:raise ValueError('현재 현금 또는 보유 수량으로 체결할 수 없는 주문입니다.')
            self.ledger().state['books'][currency]['marks'][symbol]=price
            self.ledger().save()
            return {'fill':fill,'price_source':source,'quote_as_of':str(row['date'])}

    def expert_pool(self):
        from stockrl.platform.assets import ExpertPool
        catalog=read_catalog()
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
        from stockrl.platform.expert_inference import prepare_inputs
        with self.lock:entry=self.expert_pool().entry(key)
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
        from stockrl.platform.expert_inference import run_batches
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
        from stockrl.finrl.framework import policy_files
        self.inference_active+=1
        try:
            selected=read_json(ROOT/'runtime/operations/policies.json')
            if not selected:raise ValueError('운영 정책 미승인: 모델 선택 화면에서 직접 승인하세요.')
            files=[(ROOT/'runtime/official'/path).resolve().parent for path in selected.values()]
            with self.lock:self.decisions=[]
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
        if identity.get('environment')!=CASH_ENVIRONMENT:raise ValueError('PortfolioOptimizationEnv 정책이 필요합니다. 구형 정책을 실행하지 않습니다.')
        registry=system.expert_registry(files,self.expert_pool)
        env=champion_structure_environment(identity['currency'],identity['symbols'],registry,champion_ids)
        try:
            model=system.model(policy_checkpoint(files),identity.get('algorithm','sac'),env)
            info={'path':policy_checkpoint(files).relative_to(ROOT/'runtime/official').as_posix(),'algorithm':identity.get('algorithm','sac'),'device':str(model.device),
                'observation_shape':list(model.observation_space.shape),'action_shape':list(model.action_space.shape),
                'num_timesteps':int(model.num_timesteps),'updates':int(getattr(model,'_n_updates',0))}
            if load:
                file=policy_checkpoint(files);stat=file.stat()
                self.policy_models[identity['currency']]={**info,'signature':(stat.st_mtime_ns,stat.st_size)}
                self.last_policy_dates.pop(identity['currency'],None)
            return info
        finally:env.close()

    def _sac_decision(self,files):
        identity=read_json(files/'dataset.json')
        cash_enabled=identity.get('environment')==CASH_ENVIRONMENT
        if identity.get('environment')!=CASH_ENVIRONMENT:
            raise ValueError('현재 저장 SAC는 기존 환경의 파일입니다. 현재 원본 환경으로 학습한 정책이 필요합니다.')
        symbols=identity['symbols'];currency=identity['currency'];frame=prices(currency,symbols,timeframe=policy_timeframe(identity))
        if frame.empty:
            self.status.setdefault('policy_inputs',{})[currency]={'status':'pending','detail':'실제 저장 가격이 없습니다.'}
            return
        input_stamp=str(frame.date.max());latest_rows=frame[frame.date==frame.date.max()]
        if self.last_policy_dates.get(currency)==input_stamp:return
        registry=system.expert_registry(files,self.expert_pool);champion_ids=identity.get('champion_experts',[])
        prepared=training_environment(frame,registry,training=False,champion_ids=champion_ids)
        latest=prepared.unwrapped
        latest._time_index=len(latest._sorted_times)-1
        latest._state,latest._info=latest._get_state_and_info_from_time_index(latest._time_index)
        wrapped=prepared
        try:
            file=policy_checkpoint(files);stat=file.stat();path=file.relative_to(ROOT/'runtime/official').as_posix()
            model=system.model(file,identity.get('algorithm','sac'),wrapped)
            self.policy_models[currency]={'path':path,'algorithm':identity.get('algorithm','sac'),'signature':(stat.st_mtime_ns,stat.st_size),
                'device':str(model.device),'observation_shape':list(model.observation_space.shape),'action_shape':list(model.action_space.shape),
                'num_timesteps':int(model.num_timesteps),'updates':int(getattr(model,'_n_updates',0))}
            with self.lock:
                ledger=self.ledger();book=ledger.snapshot()['books'][currency]
                history=ledger.state['books'][currency].setdefault('equity_history',[])
                if history and history[-1]['date']==input_stamp:history[-1]['nav']=book['equity']
                else:history.append({'date':input_stamp,'nav':book['equity']})
                wrapped.live_account={'currency':currency,'nav':book['equity'],'cash':book['cash'],'initial_cash':book['initial_cash'],
                    'marks':dict(book['marks']),'equity_history':[dict(point) for point in history],
                    'positions':{symbol:row['quantity'] for symbol,row in book['positions'].items()}}
            observation=wrapped.observation(latest._state)
            action,_=model.predict(observation,deterministic=True)
            import math
            allocation=latest.normalized_action(action)
            weights=allocation[1:];cash_weight=float(allocation[0])
            bars=frame[frame.date==frame.date.max()].set_index('symbol').reindex(symbols)
            stamp=str(bars.date.iloc[0])
            panel=SimpleNamespace(dates=[stamp],symbols=symbols,groups={
                s:('KRX' if s.endswith('.KS') else 'KOSDAQ' if s.endswith('.KQ') else 'US','equity') for s in symbols},
                observed=np.array([[pd.notna(bars.loc[s,'close']) and float(bars.loc[s,'close'])>0 for s in symbols]],dtype=bool),closes=np.array([[float(bars.loc[s,'close']) for s in symbols]]),
                features=np.zeros((1,len(symbols),8)))
            with self.lock:
                book=self.ledger().snapshot()['books'][currency];nav=book['equity']
                if book['cash']!=wrapped.live_account['cash'] or {s:row['quantity'] for s,row in book['positions'].items()}!=wrapped.live_account['positions']:
                    self.status.setdefault('policy_inputs',{})[currency]={'status':'pending','detail':'추론 중 보유 상태가 변경되어 다시 판단합니다.'}
                    self.feed_cycle.set();return
                panel.dates=[pd.Timestamp.now(tz='UTC').isoformat()]
                if self.controls['paper']:self.ledger().queue_allocations(panel,0,allocation,currency)
                self.ledger().save()
                self.decisions.extend({'symbol':s,'currency':currency,'target_weight':float(weight),'as_of':stamp} for s,weight in zip(symbols,weights))
                self.decisions.append({'symbol':'CASH','currency':currency,'target_weight':cash_weight,'as_of':stamp,'cash_action':cash_enabled})
                self.last_policy_dates[currency]=input_stamp
                self.status.setdefault('policy_inputs',{})[currency]={'status':'ready','as_of':stamp}
                self.status.pop('policy_error',None)
        finally:
            wrapped.close()
            if wrapped is not prepared:prepared.close()

    def close(self):
        self.command('feed',False)
        if system.expert_pool:system.expert_pool.close()

runtime=OperationsRuntime()
