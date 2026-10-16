"""Shared CMD/React orchestration of existing operations; no learner implementation."""
from ..expert_registry import read_catalog
import os,subprocess,sys,threading,time,uuid
from pathlib import Path
from datetime import datetime,timezone
import psutil
from copy import deepcopy
from .. import ROOT
from ..finrl.framework import policy_files
from ..state_io import atomic_json,read_json,update_json

RUNTIME=ROOT/'runtime/finance/policy_learning'
SERVER_RUNTIME=ROOT/'runtime/platform'

def apply_state():
    value=read_json(SERVER_RUNTIME/'apply.json',{'status':'pending','stages':[]})
    if value.get('status') in ('pending','running') and value.get('pid') and not apply_running(value):
        value={**value,'status':'failed','error':'변경 적용 프로세스가 종료됐습니다. 저장된 실패 단계와 로그를 확인하세요.'}
    return value

def apply_running(value=None):
    value=value or read_json(SERVER_RUNTIME/'apply.json')
    if value.get('status') not in ('pending','running'):return False
    try:
        process=psutil.Process(value['pid'])
        return abs(process.create_time()-value['process_created'])<.01 and any('start_server.py' in arg for arg in process.cmdline())
    except (psutil.Error,KeyError):return False

def start_apply(target='frontend'):
    if target not in ('frontend','backend','all'):raise ValueError('frontend, backend, all 중 적용 대상을 선택하세요.')
    with system.job_lock:
        if apply_running():return apply_state()
        env=os.environ.copy();env.update(PYTHONPATH=str(ROOT/'backend'),PYTHONUTF8='1')
        SERVER_RUNTIME.mkdir(parents=True,exist_ok=True)
        with (SERVER_RUNTIME/'apply-launch.log').open('ab') as output:
            args=[sys.executable,str(ROOT/'development/scripts/start_server.py'),'--apply-only','--skip-checks']
            if target=='frontend':args.append('--frontend-only')
            elif target=='backend':args.append('--skip-build')
            child=subprocess.Popen(args,cwd=ROOT,env=env,
                stdout=output,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        value={'status':'running','target':target,'pid':child.pid,'process_created':psutil.Process(child.pid).create_time(),
            'stages':[{'id':'queue','title':'변경 적용 요청','status':'pending','detail':'독립 런처에서 처리합니다.'}]}
        atomic_json(value,SERVER_RUNTIME/'apply.json')
        return value

def busy():
    from ai_agent.Hermes.engine.bridge import bridge
    from stockrl.trading.operation_control.operations_runtime import runtime
    from .library_operations import library
    items=[]
    if system.job_state()['running']:items.append('실행 중인 SAC/백테스트/수집 작업')
    if runtime.thread and runtime.thread.is_alive():items.append('실행 중인 시세 수신')
    if runtime.controls['paper']:items.append('활성 가상매매')
    if runtime.controls['engine'] or runtime.inference_active:items.append('활성 추론')
    if runtime.controls['learning']:items.append('활성 지속학습')
    if library.active:items.append('실행 중인 모델 작업')
    if system.active:items.append('전체 시스템 시작 절차')
    hermes=bridge.busy_reason()
    if hermes:items.append(hermes)
    return items

def check_system():
    from stockrl.extensions.moe import handlers as _moe_api
    from stockrl.finrl.policy_learning import handlers as _policy_learning_api
    from stockrl.management.connection_settings import handlers as _connection_settings_api
    from stockrl.management.diagnostics_logs_code_apply import handlers as _diagnostics_api
    from stockrl.trading.operation_control.operations_runtime import runtime
    from stockrl.trading.operation_control.operations_settings import settings
    from stockrl.management.connection_settings.provider_credentials import public_status
    items=[]
    def check(key,title,function):
        try:
            status,detail=function();items.append(dict(id=key,title=title,status=status,detail=detail))
        except Exception as exc:items.append(dict(id=key,title=title,status='failed',detail=str(exc)))
    cfg=settings()
    def framework():
        value=_policy_learning_api.source_settings()
        return 'complete','원본 SAC 설정·환경 경로·설치 버전 조회: '+str(value['versions'])+'; 학습 미실행'
    check('framework','FinRL · SB3',framework)
    def policy():
        value=_policy_learning_api.model_state(_policy_learning_api.source_settings())
        if not value['policy_compatible']:return 'blocked','SAC 관측·행동 구조 비호환: '+' · '.join(value['structure_reasons'])
        if not value['compatible']:return 'blocked','정책 구조는 호환; 이어 학습 상태 미충족: '+' · '.join(value['resume_reasons'])
        return 'complete','현재 SAC 구조·이어 학습 Replay 호환; Expert 추론·시세 수신과 별도 확인'
    check('policy','SAC 체크포인트 · Replay',policy)
    check('models','외부 모델 폴더',lambda:('complete',str(cfg.model_dir)) if cfg.model_dir.is_dir() else ('blocked','모델 폴더 없음: '+str(cfg.model_dir)))
    def experts():
        value=_moe_api.expert_state();active=[row for row in value['items'] if row['active']]
        missing=[row['id'] for row in active if not row['package_available']]
        return ('blocked','선택 패키지 없음/크기 불일치: '+', '.join(missing)) if missing else ('complete',f"등록 {len(value['items'])}, 선택 {len(active)}, API 적재 {sum(row['loaded'] for row in value['items'])}; 파일 존재·크기 확인, 추론 미실행")
    check('experts','Frozen Expert 등록 · 선택 · 적재',experts)
    check('accounts','KRW/USD 가상계좌',lambda:('complete','기존 PaperAccount 원장 조회; 주문·초기화 미실행; 통화 '+', '.join(runtime.ledger().snapshot()['books'])))
    def data():
        value=_diagnostics_api.database()
        if value.get('error'):return 'failed',value['error']
        return ('complete',f"저장 가격 {value['rows']}행 / {value['tickers']}종목") if value['rows'] else ('blocked','저장 가격 없음')
    check('data','저장 데이터',data)
    def provider():
        value=public_status(cfg.state_dir)
        if value.get('vault_error'):return 'failed',value['vault_error']
        if value['provider']=='kiwoom' and not value['saved']:return 'blocked','키움 인증 미저장'
        return 'complete',value['provider_name']+' 설정 조회; 외부 인증 요청 미실행'
    check('provider','저장 인증 · 시세 공급원',provider)
    def collection():
        value=_connection_settings_api.connections()['data']
        return ('complete','공식 가격 수집 공급원 설정 있음; 원격 수집 미실행') if value['status']=='configured' else ('blocked',value.get('reason') or value['status'])
    check('collection','금융 가격 수집 연결',collection)
    def feed():
        value=runtime.status
        if value.get('error'):return 'failed',value['error']
        if runtime.controls['feed'] and value.get('last_received_at'):return 'complete','실제 완료 바 수신 기록: '+str(value.get('last_as_of'))
        if not runtime.controls['feed']:return 'pending','시세 수신 중지 상태; 시작 명령 전에는 실제 수신을 확인하지 않습니다.'
        return 'blocked','시세 수신 '+value['status']+'; 현재 수신은 확인하지 않음'
    check('feed','실제 시장 데이터 수신',feed)
    check('workers','현재 작업 상태',lambda:('complete',' · '.join(busy()) or '실행 중 운영 작업 없음; 상태만 조회'))
    return {'items':items}

class SystemOperations:
    def __init__(self):
        self.path=ROOT/'runtime/finance/operation_control/system.json';self.lock=threading.RLock()
        self.job_lock=threading.RLock();self.job_process=None
        self.active=False;self.cancelled=threading.Event();self.restarting=False
        self.value=read_json(self.path,{'status':'pending','stages':[]})
        self.state_lock=threading.RLock();self.model_lock=threading.RLock()
        self.states={};self.state_signatures={};self.state_errors={};self.state_updates={};self.state_revision=0
        self.state_loader_locks={}
        self.command_router=None
        self.model_cache={};self.registry_cache={};self.expert_pool=None;self.expert_pool_signature=None
        from ..state_io import subscribe_updates
        subscribe_updates(self.module_update)
    def commands(self):
        return [{'operation':route.path.removeprefix('/api/'),'methods':sorted(route.methods or ()),
            'module':route.endpoint.__module__,'function':route.endpoint.__name__}
            for route in self.command_router.routes if hasattr(route,'endpoint') and route.path.startswith('/api/')]

    def process_for(self,job):
        try:
            process = psutil.Process(int(job["pid"]))
            if job.get("process_created") and abs(process.create_time() - job["process_created"]) > 0.1:
                return None
            if process.is_running() and any(x in " ".join(process.cmdline()) for x in ("stockrl.job_worker", "stockrl.finrl.policy_learning.official_cli")):
                return process
        except (psutil.Error, KeyError, ValueError):
            pass
        return None

    def job_state(self):
        job = read_json(RUNTIME / "job.json")
        if self.job_process and self.job_process.poll() is not None:self.job_process=None
        process = self.process_for(job) if job else None
        if job.get("status") in ("starting", "running") and not process:
            job["status"] = "unknown"
            job["detail"] = "프로세스가 종료됐지만 완료 기록이 없습니다. 로그를 확인하세요."
        result = {**job, "running": process is not None, "log_text": ""}
        name = job.get("log", "training.log")
        path = RUNTIME / name
        if path.is_file() and path.resolve().is_relative_to(RUNTIME.resolve()):
            with path.open("rb") as stream:
                stream.seek(max(0, path.stat().st_size - 32000))
                result["log_text"] = stream.read().decode("utf8", errors="replace")
        import re
        measured={}
        for key,value in re.findall(r"\|\s*([a-z_]+)\s*\|\s*([-+\deE.]+)\s*\|",result["log_text"]):
            try: measured[key]=float(value)
            except ValueError: pass
        result["measurements"]=measured
        return result

    def start_job(self,job):
        with self.job_lock:
            RUNTIME.mkdir(parents=True,exist_ok=True);(RUNTIME/'jobs').mkdir(exist_ok=True)
            env=os.environ.copy();env.update(PYTHONPATH=str(ROOT/'backend'),PYTHONUTF8='1')
            from ..finrl.provider_settings.operations import provider_environment
            env.update(provider_environment())
            with (RUNTIME/job['log']).open('w',encoding='utf8') as output:
                process=subprocess.Popen([sys.executable,'-m','stockrl.job_worker',job['id']],cwd=ROOT,env=env,
                    stdout=output,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            job.update(pid=process.pid,process_created=psutil.Process(process.pid).create_time())
            self.job_process=process
            atomic_json(job,RUNTIME/'jobs'/(job['id']+'.json'))
            update_json(RUNTIME/'job.json',lambda current:dict(job) if current.get('id')!=job['id'] else {**job,**current,'pid':job['pid'],'process_created':job['process_created']})
            (RUNTIME/'training.pid').write_text(str(process.pid))
            return job

    def stop_job(self):
        with self.job_lock:
            job = read_json(RUNTIME / "job.json")
            process = self.process_for(job)
            if not process:
                raise RuntimeError( "실행 중인 작업이 없습니다.")
            descendants = process.children(recursive=True)
            for child in reversed(descendants):
                try:
                    child.terminate()
                except psutil.Error:
                    pass
            process.terminate()
            psutil.wait_procs([*descendants, process], timeout=3)
            for child in [*descendants, process]:
                try:
                    if child.is_running():
                        child.kill()
                except psutil.Error:
                    pass
            job.update(status="stopped", finished_at=datetime.now(timezone.utc).isoformat(), detail="사용자가 중단했습니다. 정상 종료 전 새 가중치는 저장되지 않습니다.")
            update_json(RUNTIME/'job.json',lambda current:{**current,'status':job['status'],'finished_at':job['finished_at'],'detail':job['detail']} if current.get('id')==job['id'] else None)
            update_json(RUNTIME/'jobs'/(job['id']+'.json'),lambda current:{**current,'status':job['status'],'finished_at':job['finished_at'],'detail':job['detail']} if current.get('id')==job['id'] else None)
            return {"message": job["detail"]}
    def module_update(self,path,value):
        path=Path(path).resolve()
        if not path.is_relative_to(ROOT.resolve()):return
        with self.state_lock:
            for name,signature in list(self.state_signatures.items()):
                if isinstance(signature,tuple) and any(isinstance(row,tuple) and row and row[0]==str(path) for row in signature):
                    self.state_signatures.pop(name,None)
    def publish(self,name,value,signature=None):
        with self.state_lock:
            self.states[name]=deepcopy(value);self.state_signatures[name]=signature
            self.state_errors.pop(name,None);self.state_revision+=1;self.state_updates[name]=time.time()
            return self.states[name]
    def state_value(self,name,loader,signature=None):
        with self.state_lock:lock=self.state_loader_locks.setdefault(name,threading.RLock())
        with lock:
            try:
                signature=signature() if callable(signature) else signature
                with self.state_lock:
                    if signature is not None and name not in self.state_errors and name in self.states and self.state_signatures.get(name)==signature:return self.states[name]
                return self.publish(name,loader(),signature)
            except Exception as exc:
                with self.state_lock:
                    self.state_errors[name]=str(exc);self.state_revision+=1
                    self.state_signatures.pop(name,None)
                    return self.states.get(name)
    def invalidate_states(self):
        with self.state_lock:self.state_signatures.clear()
    def prune_missing_file_states(self,prefix):
        with self.state_lock:
            caches=(self.states,self.state_signatures,self.state_errors,self.state_updates)
            names=set().union(*(cache.keys() for cache in caches))
            missing=[name for name in names if name.startswith(prefix) and not Path(name[len(prefix):]).is_file()]
            for name in missing:
                for cache in caches:cache.pop(name,None)
            if missing:self.state_revision+=1
    def connect_modules(self):
        import importlib
        import sys
        from ..finrl.framework import finrl_file
        modules={
            'stockrl':['live_feed','platform.kiwoom_data','platform.assets','platform.expert_inference','platform.expert_conversion','platform.sac_champion'],
            'FinRL':['meta.env_portfolio_optimization.env_portfolio_optimization','meta.preprocessor.preprocessors','agents.stablebaselines3.models']}
        result={}
        for framework,names in modules.items():
            for name in names:
                key=framework+':'+name
                def load(framework=framework,name=name):
                    if framework=='FinRL' and name.startswith('meta.env_portfolio_optimization.'):
                        module=finrl_file(name.replace('.','/')+'.py')
                    else:module=importlib.import_module(('finrl' if framework=='FinRL' else 'stockrl')+'.'+name)
                    return {'imported':True,'file':getattr(module,'__file__',None)}
                value=self.state_value('import:'+key,load,())
                result[key]={**(value or {'imported':False}),'error':self.state_errors.get('import:'+key,'')}
        return result
    def model(self,path,algorithm,environment=None):
        from finrl.agents.stablebaselines3.models import MODELS
        path=Path(path).resolve()
        if path.is_relative_to((ROOT/'휴지통').resolve()):raise ValueError('휴지통은 모델 실행에 사용하지 않습니다.')
        stamp=path.stat();signature=(stamp.st_mtime_ns,stamp.st_size,algorithm)
        with self.model_lock:
            key=str(path);entry=self.model_cache.get(key)
            if entry is None or entry['signature']!=signature:
                loads=1+(entry['loads'] if entry else 0)
                self.model_cache.pop(key,None);entry=None
                self.release_models(keep=self.selected_models()|{key})
                model=MODELS[algorithm].load(path,env=environment)
                entry={'model':model,'signature':signature,'algorithm':algorithm,'loads':loads,'reuse':0}
                self.model_cache[key]=entry
            else:
                entry['reuse']+=1
                if environment is not None:entry['model'].set_env(environment)
            entry['last_used']=time.monotonic()
            return entry['model']
    def selected_models(self):
        return {str((RUNTIME/path).resolve()) for path in read_json(ROOT/'runtime/finance/operation_control/policies.json').values()}
    def release_models(self,keep=(),force=False):
        # Retain approved policies and the currently requested model; release older transient uses.
        released=False
        with self.model_lock:
            for key in sorted(self.model_cache,key=lambda key:self.model_cache[key].get('last_used',0)):
                if key not in keep:del self.model_cache[key];released=True
        if not released and not force:return
        import gc
        gc.collect()
        import torch
        if torch.cuda.is_available():torch.cuda.empty_cache()
    def close_models(self):
        with self.model_lock:
            self.model_cache.clear()
            for entry in self.registry_cache.values():entry['registry'].close(cleanup=True)
            self.registry_cache.clear()
        self.release_models(force=True)
    def expert_registry(self,folder,pool_provider,champion=None,champion_path=None):
        from ..expert_registry_native import ExpertRegistry
        from .sac_champion import load_spec
        folder=Path(folder).resolve();identity=read_json(folder/'dataset.json');champion_path=champion_path or identity.get('champion_file')
        signature=None
        if champion_path:
            path=Path(champion_path).resolve();stamp=path.stat();signature=(str(path),stamp.st_mtime_ns,stamp.st_size)
        key=(str(champion_path) if champion_path else 'shared',identity.get('currency'),tuple(identity.get('symbols',[])),tuple(identity.get('champion_experts',[])),identity.get('environment'))
        with self.model_lock:
            entry=self.registry_cache.get(key)
            if entry is None or entry['signature']!=signature:
                registry=ExpertRegistry(champion=champion if champion is not None else load_spec(champion_path)) if champion_path else ExpertRegistry(pool_provider)
                for old in list(self.registry_cache):
                    if old!=key and old[1]==key[1]:self.registry_cache.pop(old)['registry'].close(cleanup=True)
                if entry:entry['registry'].close(cleanup=True)
                entry={'registry':registry,'signature':signature};self.registry_cache[key]=entry
            return entry['registry']
    def resident_models(self):
        with self.model_lock:return [{'path':path,'algorithm':row['algorithm'],'device':str(row['model'].device),
            'loads':row['loads'],'reuse':row['reuse']} for path,row in self.model_cache.items()]
    def snapshot(self):
        with self.lock:
            value={**deepcopy(self.value),'active':self.active}
            if value.get('stop_requested'):
                from stockrl.trading.operation_control.operations_runtime import runtime
                from .library_operations import library
                pending=bool(self.active or runtime.inference_active or library.active or runtime.thread and runtime.thread.is_alive())
                value['status']='running' if pending else 'complete'
                row=next((row for row in value['stages'] if row['id']=='stop'),None)
                if row:row.update(status='running' if pending else 'complete',detail='작업 종료 대기' if pending else '운영 중지; 저장 데이터와 관리 서버 유지')
            elif value.get('status')=='running' and not self.active:
                value.update(status='blocked',detail='이전 시작 절차가 중단됐습니다. 실제 작업 상태는 개별 제어에서 확인하세요.')
            return value
    def phase(self,key,title,status='running',detail='',**extra):
        with self.lock:
            row=next((row for row in self.value['stages'] if row['id']==key),None)
            if row is None:row=dict(id=key,title=title);self.value['stages'].append(row)
            row.update(status=status,detail=detail,**extra);atomic_json(self.value,self.path)
    def interrupted(self):
        if self.cancelled.is_set():raise InterruptedError('사용자의 개별 제어/중지 요청으로 자동 절차를 멈췄습니다.')
    def cancel(self):
        self.cancelled.set()
    def start(self,currencies=None):
        from .library_operations import library
        with self.lock:
            if self.active:return self.snapshot()
            from stockrl.trading.operation_control.operations_runtime import runtime
            if self.value.get('status')=='complete' and all(runtime.controls[name] for name in ('feed','paper','engine','learning')) and self.value.get('currencies')==(currencies or ['USD','KRW']):return self.snapshot()
            if apply_running() or self.restarting:raise ValueError('변경 적용이 끝난 후 운영을 시작하세요.')
            if library.active:raise ValueError('현재 모델 작업이 끝난 후 전체 시작을 요청하세요.')
            self.cancelled.clear();self.active=True
            runtime.cancel_inference.clear()
            self.value=dict(id=uuid.uuid4().hex,status='running',started_at=time.time(),stages=[],currencies=currencies or ['USD','KRW'])
            phases=[('accounts','KRW/USD 가상계좌 준비'),('experts','선택 Frozen Expert 적재')]
            for currency in self.value['currencies']:phases.extend([('policy-'+currency,currency+' SAC 정책 호환성'),('train-'+currency,currency+' 신규 SAC 학습')])
            phases.extend([('connection','인증 · 실제 시세 연결'),('trading','실제 입력 추론 · 가상매매'),('learning','선택 정책 지속학습')])
            self.value['stages']=[dict(id=key,title=title,status='pending') for key,title in phases]
            atomic_json(self.value,self.path)
            threading.Thread(target=self.run,name='system-start',daemon=True).start()
            return self.snapshot()
    def run(self):
        
        from stockrl.trading.operation_control.operations_runtime import runtime
        from stockrl.trading.operation_control.operations_settings import settings
        from stockrl.management.connection_settings.provider_credentials import public_status
        from stockrl.management.connection_settings.provider_credentials import test_connection
        cfg=settings()
        try:
            key='accounts';title='KRW/USD 가상계좌 준비';self.phase(key,title)
            runtime.ledger().save();self.phase(key,title,'complete','기존 잔고·보유·체결 원장 유지')
            self.interrupted();key='experts';title='선택 Frozen Expert 적재';self.phase(key,title)
            if not cfg.model_dir.is_dir():raise ValueError('모델 폴더 없음: '+str(cfg.model_dir))
            catalog=read_catalog(cfg.registry_file)
            selected_policies=read_json(ROOT/'runtime/finance/operation_control/policies.json')
            identities=[read_json((RUNTIME/selected_policies.get(currency,'')).parent/'dataset.json') for currency in self.value['currencies']]
            expert_ids={expert for identity in identities for expert in identity.get('champion_experts',[])} or set(catalog.get('active',[]))
            required={symbol for expert in expert_ids for symbol in ((catalog['experts'].get(expert,{}).get('input') or {}).get('universe') or [])}
            if required:
                from ..finrl.price_data.operations import prices,collect_kiwoom_prices
                history=prices('USD',sorted(required))
                missing=sorted(required-(set(history.symbol) if not history.empty else set()))
                if missing:
                    self.phase(key,title,detail='원본 Expert의 키움 미국 일봉 수집: '+', '.join(missing))
                    collected=collect_kiwoom_prices(missing,currency='USD')
                    if collected['errors']:raise ValueError('Expert 원본 입력 수집 실패: '+str(collected['errors']))
            embedded_models=all(read_json((RUNTIME/selected_policies.get(currency,'')).parent/'dataset.json').get('champion_file') for currency in self.value['currencies'])
            preload=[] if embedded_models else catalog.get('active',[])
            for expert in preload:
                self.interrupted();self.phase(key,title,detail=expert);runtime.load(expert)
            self.phase(key,title,'complete','선택 Champion의 Frozen Expert는 추론 시 내부 구성으로 사용합니다.' if embedded_models else f"사용자 선택 {len(preload)}개 적재; 선택 구성 유지")
            ready_policies={};failures=[]
            for currency in self.value['currencies']:
                self.interrupted();key='policy-'+currency;title=currency+' SAC 정책 호환성';self.phase(key,title)
                if selected_policies.get(currency):
                    path=(RUNTIME/selected_policies[currency]).resolve()
                    try:
                        from ..finrl.framework import policy_checkpoint
                        if not path.is_relative_to(RUNTIME.resolve()) or path!=policy_checkpoint(path.parent) or read_json(path.parent/'dataset.json').get('currency')!=currency:
                            raise ValueError('선택한 운영 정책의 경로 또는 통화가 다릅니다.')
                        runtime.check_policy(path.parent,load=True)
                    except (ValueError,RuntimeError,OSError,KeyError,MemoryError) as exc:
                        reason=currency+' 선택 모델 로딩 실패: '+str(exc);failures.append(reason);self.phase(key,title,'blocked',reason);continue
                    ready_policies[currency]=path.relative_to(RUNTIME).as_posix()
                    self.phase(key,title,'complete','사용자가 선택한 운영 모델 로드: '+str(path))
                    self.phase('train-'+currency,currency+' 신규 SAC 학습','complete','선택 모델 유지; 자동 대체·새 학습 없음')
                    continue
                reason=currency+' 운영 정책 미승인: 모델 선택 화면에서 저장 정책을 직접 승인하세요.'
                failures.append(reason);self.phase(key,title,'blocked',reason)
                self.phase('train-'+currency,currency+' 신규 SAC 학습','blocked','자동 학습·운영 승격 없음; 학습과 정책 승인은 별도 명령입니다.')
            # Stored-data SAC preparation is independent of a live market connection.
            key='connection';title='인증 · 실제 시세 연결'
            connection_error=None
            try:
                self.phase(key,title);cfg=settings();provider=public_status(cfg.state_dir)
                if provider.get('vault_error'):raise ValueError(provider['vault_error'])
                if provider['provider']=='kiwoom':
                    if not provider['saved']:raise ValueError('키움 저장 인증 정보가 없습니다.')
                    tested=test_connection(cfg.state_dir)
                    if not tested['ok']:raise ValueError(tested['message'])
                self.interrupted();runtime.command('feed',True)
                # One existing collection cycle. Closed markets/errors remain visible, with no fabricated quotes.
                while not runtime.feed_cycle.wait(1):
                    self.interrupted()
                    if runtime.status.get('error'):raise ValueError(runtime.status['error'])
                    if not runtime.controls['feed']:raise ValueError('시세 수신 작업이 중지됐습니다.')
                self.interrupted()
                if runtime.status.get('error'):raise ValueError(runtime.status['error'])
                if provider['provider']=='kiwoom' and not (runtime.collector and runtime.collector.broker_status.get('connected') and runtime.collector.broker_status.get('last_message_utc')):
                    raise ValueError('키움 실제 시세 수신 미확인: '+str(runtime.collector.broker_status.get('last_error') if runtime.collector else '수신 작업 종료'))
                if not runtime.status.get('last_received_at'):
                    metrics=read_json(cfg.state_dir/'live/live_feed_metrics.json')
                    raise ValueError('완료 시장 데이터 미수신: '+str(metrics.get('broker_error') or metrics.get('retrying_symbols') or '휴장·입력 없음; 기존 시세 상태 확인 필요'))
                self.phase(key,title,'complete','실제 완료 바 수신 확인; '+provider['provider_name'])
            except InterruptedError:
                raise
            except Exception as exc:
                connection_error=str(exc)
                runtime.command('feed',False)
                self.phase(key,title,'blocked' if isinstance(exc,ValueError) else 'failed',connection_error)
                failures.append('시세 수신: '+connection_error)
            self.interrupted();key='trading';title='실제 입력 추론 · 가상매매';self.phase(key,title)
            if not ready_policies:raise ValueError('준비된 SAC 정책이 없습니다. 통화별 준비 부족 사유를 확인하세요.')
            if connection_error:
                self.phase(key,title,'blocked','저장 데이터의 SAC 준비는 완료됐지만 실시간 시세 미수신으로 추론·가상매매를 시작하지 않았습니다.')
                with self.lock:
                    self.value.update(status='blocked',detail=' · '.join(failures),finished_at=time.time())
                    atomic_json(self.value,self.path)
                return
            with runtime.lock:
                self.interrupted()
                runtime.command('paper',True);runtime.command('engine',True);runtime.command('learning',True)
            runtime.sac_decision()
            pending=[currency for currency in ready_policies if runtime.status.get('policy_inputs',{}).get(currency,{}).get('status')!='ready']
            if pending:raise ValueError('선택 종목의 실제 가격 행렬이 준비되지 않아 추론을 실행하지 않았습니다: '+', '.join(pending))
            report=read_json(ROOT/'runtime/finance/moe/status.json')
            failures.extend(expert+': '+str(row.get('reason','Expert 추론 실패')) for expert,row in report.get('experts',{}).items() if expert in catalog.get('active',[]) and row.get('status')!='ready')
            self.phase(key,title,'complete',', '.join(ready_policies)+' 실제 가격·Expert 관측으로 SAC 판단 실행; 이후 완료 바에서 기존 가상체결. 실제 증권 주문 미전송')
            self.phase('learning','선택 정책 지속학습','complete','기존 모델·Replay로 새 완료 입력을 이어 학습; 원본 Expert는 동결 유지')
            with self.lock:
                self.value.update(status='blocked' if failures else 'complete',detail=' · '.join(failures) if failures else '전체 운영 시작',finished_at=time.time());atomic_json(self.value,self.path)
        except Exception as exc:
            if key=='trading':runtime.command('learning',False);runtime.command('engine',False);runtime.command('paper',False)
            self.phase(key,title,'blocked' if isinstance(exc,InterruptedError) or isinstance(exc,ValueError) else 'failed',str(exc))
            with self.lock:self.value.update(status='blocked' if isinstance(exc,(InterruptedError,ValueError)) else 'failed',detail=str(exc));atomic_json(self.value,self.path)
        finally:self.active=False
    def stop(self):
        from stockrl.trading.operation_control.operations_runtime import runtime
        from .library_operations import library
        self.cancel();library.cancelled.set();runtime.cancel_inference.set()
        runtime.command('learning',False);runtime.command('engine',False);runtime.command('paper',False);runtime.command('feed',False)
        if system.job_state()['running']:stop()
        if runtime.account:runtime.account.save()
        pending=bool(runtime.inference_active or library.active or runtime.thread and runtime.thread.is_alive() or self.active)
        self.phase('stop','전체 시스템 중지','running' if pending else 'complete','현재 추론/수신 작업 종료 대기' if pending else '운영 중지; 서버·모델·계좌 파일 유지')
        self.value.update(status='running' if pending else 'complete',detail='중지 요청 처리',stop_requested=True);atomic_json(self.value,self.path)
        return {'message':'운영 중지 요청을 처리했습니다. 현재 작업 종료 상태는 화면에서 확인하세요.','pending':pending}

system=SystemOperations()
