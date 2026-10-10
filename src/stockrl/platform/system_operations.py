"""Shared CMD/React orchestration of existing operations; no learner implementation."""
import os,subprocess,sys,threading,time,uuid
from pathlib import Path
import psutil
from copy import deepcopy
from ..framework import ROOT,policy_files
from ..state_io import atomic_json,read_json

RUNTIME=ROOT/'runtime/official'

def apply_state():
    value=read_json(RUNTIME/'apply.json',{'status':'pending','stages':[]})
    if value.get('status') in ('pending','running') and value.get('pid') and not apply_running(value):
        value={**value,'status':'failed','error':'변경 적용 프로세스가 종료됐습니다. 저장된 실패 단계와 로그를 확인하세요.'}
    return value

def apply_running(value=None):
    value=value or read_json(RUNTIME/'apply.json')
    if value.get('status') not in ('pending','running'):return False
    try:
        process=psutil.Process(value['pid'])
        return abs(process.create_time()-value['process_created'])<.01 and any('start_server.py' in arg for arg in process.cmdline())
    except (psutil.Error,KeyError):return False

def start_apply():
    from ..web_api import launch_lock
    with launch_lock:
        if apply_running():return apply_state()
        env=os.environ.copy();env.update(PYTHONPATH=str(ROOT/'src'),PYTHONUTF8='1')
        RUNTIME.mkdir(parents=True,exist_ok=True)
        with (RUNTIME/'apply-launch.log').open('ab') as output:
            child=subprocess.Popen([sys.executable,str(ROOT/'scripts/start_server.py'),'--apply-only'],cwd=ROOT,env=env,
                stdout=output,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        value={'status':'running','pid':child.pid,'process_created':psutil.Process(child.pid).create_time(),
            'stages':[{'id':'queue','title':'변경 적용 요청','status':'pending','detail':'독립 런처에서 처리합니다.'}]}
        atomic_json(value,RUNTIME/'apply.json')
        return value

def busy():
    from ..web_api import job_state
    from .operations_runtime import runtime
    from .library_operations import library
    items=[]
    if job_state()['running']:items.append('실행 중인 SAC/백테스트/수집 작업')
    if runtime.thread and runtime.thread.is_alive():items.append('실행 중인 시세 수신')
    if runtime.controls['paper']:items.append('활성 가상매매')
    if runtime.controls['engine'] or runtime.inference_active:items.append('활성 추론')
    if library.active:items.append('실행 중인 모델 작업')
    if system.active:items.append('전체 시스템 시작 절차')
    return items

def check_system():
    from .. import web_api as api
    from .operations_runtime import runtime
    from .operations_settings import settings
    from ..provider_credentials import public_status
    items=[]
    def check(key,title,function):
        try:
            status,detail=function();items.append(dict(id=key,title=title,status=status,detail=detail))
        except Exception as exc:items.append(dict(id=key,title=title,status='failed',detail=str(exc)))
    cfg=settings()
    def framework():
        value=api.source_settings()
        return 'complete','원본 SAC 설정·환경 경로·설치 버전 조회: '+str(value['versions'])+'; 학습 미실행'
    check('framework','FinRL-X · FinRL · SB3',framework)
    def policy():
        value=api.model_state(api.source_settings())
        return ('complete','현재 정책 식별·구조·Replay 메타데이터 호환; 추론 미실행') if value['compatible'] else ('blocked',' · '.join(value['reasons']))
    check('policy','SAC 체크포인트 · Replay',policy)
    check('models','외부 모델 폴더',lambda:('complete',str(cfg.model_dir)) if cfg.model_dir.is_dir() else ('blocked','모델 폴더 없음: '+str(cfg.model_dir)))
    def experts():
        value=api.expert_state();active=[row for row in value['items'] if row['active']]
        missing=[row['id'] for row in active if not row['package_available']]
        return ('blocked','선택 패키지 없음/크기 불일치: '+', '.join(missing)) if missing else ('complete',f"등록 {len(value['items'])}, 선택 {len(active)}, API 적재 {sum(row['loaded'] for row in value['items'])}; 파일 존재·크기 확인, 추론 미실행")
    check('experts','Frozen Expert 등록 · 선택 · 적재',experts)
    check('accounts','KRW/USD 가상계좌',lambda:('complete','기존 PaperAccount 원장 조회; 주문·초기화 미실행; 통화 '+', '.join(runtime.ledger().snapshot()['books'])))
    def data():
        value=api.database()
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
        value=api.connections()['data']
        return ('complete','공식 가격 수집 공급원 설정 있음; 원격 수집 미실행') if value['status']=='configured' else ('blocked',value.get('reason') or value['status'])
    check('collection','FinRL-X 가격 수집 연결',collection)
    def feed():
        value=runtime.status
        if value.get('error'):return 'failed',value['error']
        if runtime.controls['feed'] and value.get('last_received_at'):return 'complete','실제 완료 바 수신 기록: '+str(value.get('last_as_of'))
        return 'blocked','시세 수신 '+value['status']+'; 현재 수신은 확인하지 않음'
    check('feed','실제 시장 데이터 수신',feed)
    check('workers','현재 작업 상태',lambda:('complete',' · '.join(busy()) or '실행 중 운영 작업 없음; 상태만 조회'))
    return {'items':items}

class SystemOperations:
    def __init__(self):
        self.path=ROOT/'runtime/operations/system.json';self.lock=threading.RLock()
        self.active=False;self.cancelled=threading.Event();self.restarting=False
        self.value=read_json(self.path,{'status':'pending','stages':[]})
    def snapshot(self):
        with self.lock:
            value={**deepcopy(self.value),'active':self.active}
            if value.get('stop_requested'):
                from .operations_runtime import runtime
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
            from .operations_runtime import runtime
            if self.value.get('status')=='complete' and all(runtime.controls.values()) and self.value.get('currencies')==(currencies or ['USD','KRW']):return self.snapshot()
            if apply_running() or self.restarting:raise ValueError('변경 적용이 끝난 후 운영을 시작하세요.')
            if library.active:raise ValueError('현재 모델 작업이 끝난 후 전체 시작을 요청하세요.')
            self.cancelled.clear();self.active=True
            runtime.cancel_inference.clear()
            self.value=dict(id=uuid.uuid4().hex,status='running',started_at=time.time(),stages=[],currencies=currencies or ['USD','KRW'])
            phases=[('connection','인증 · 실제 시세 연결'),('accounts','KRW/USD 가상계좌 준비'),('experts','선택 Frozen Expert 적재')]
            for currency in self.value['currencies']:phases.extend([('policy-'+currency,currency+' SAC 정책 호환성'),('train-'+currency,currency+' 신규 SAC 학습')])
            phases.append(('trading','실제 입력 추론 · 가상매매'))
            self.value['stages']=[dict(id=key,title=title,status='pending') for key,title in phases]
            atomic_json(self.value,self.path)
            threading.Thread(target=self.run,name='system-start',daemon=True).start()
            return self.snapshot()
    def run(self):
        from .. import web_api as api
        from .operations_runtime import runtime
        from .operations_settings import settings
        from ..provider_credentials import public_status,test_connection
        key='connection';title='인증 · 실제 시세 연결'
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
            key='accounts';title='KRW/USD 가상계좌 준비';self.phase(key,title)
            runtime.ledger().save();self.phase(key,title,'complete','기존 잔고·보유·체결 원장 유지')
            self.interrupted();key='experts';title='선택 Frozen Expert 적재';self.phase(key,title)
            if not cfg.model_dir.is_dir():raise ValueError('모델 폴더 없음: '+str(cfg.model_dir))
            catalog=read_json(cfg.registry_file)
            for expert in catalog.get('active',[]):
                self.interrupted();self.phase(key,title,detail=expert);runtime.load(expert)
            self.phase(key,title,'complete',f"사용자 선택 {len(catalog.get('active',[]))}개 적재; 선택 구성 유지")
            ready_policies={};failures=[]
            for currency in self.value['currencies']:
                self.interrupted();key='policy-'+currency;title=currency+' SAC 정책 호환성';self.phase(key,title)
                symbols=[row['symbol'] for row in api.database()['instruments'] if row['eligible'] and row['currency']==currency and (not cfg.symbols or row['symbol'] in cfg.symbols)] if cfg.symbols else []
                if cfg.symbols and not symbols:
                    reason='운영 설정에서 선택한 '+currency+' 종목이 없습니다.';failures.append(reason);self.phase(key,title,'blocked',reason);continue
                request=api.RunRequest(currency=currency,symbols=symbols)
                checked=api.preflight(request,'train')
                rows=[policy_files(),*[RUNTIME/row['path'] for row in api.checkpoints(api.source_settings())]]
                selected=None
                for path in rows:
                    folder=path.parent if path.suffix=='.zip' else path
                    model=api.model_state(api.source_settings(),folder)
                    if model.get('policy_compatible',model['compatible']) and model['identity'].get('currency')==currency and model['identity'].get('symbols')==checked['symbols']:
                        selected=folder;break
                if selected is None:
                    if not checked['ok']:
                        reason=' · '.join(checked['errors']);failures.append(currency+': '+reason);self.phase(key,title,'blocked',reason);continue
                    self.phase(key,title,'blocked','호환 정책 없음; 기존 파일 보존 후 신규 학습 준비')
                    key='train-'+currency;title=currency+' 신규 SAC 학습';self.phase(key,title)
                    current=api.job_state()
                    if current['running']:
                        self.phase(key,title,'blocked','기존 개별 학습/평가/수집을 보존합니다. 종료 후 다시 시작하세요.');failures.append(currency+': 기존 작업 실행 중');continue
                    self.interrupted();launched=api.launch('train',request,preserve_output=True)['job']
                    while True:
                        self.interrupted();job=api.job_state()
                        self.phase(key,title,detail=f"작업 {launched['id']} · {job['status']}",job_id=launched['id'],log=job.get('log'))
                        if job.get('id')!=launched['id']:raise ValueError('개별 명령이 학습 작업을 교체했습니다. 자동 절차를 종료합니다.')
                        if not job['running']:
                            if job['status']!='succeeded':raise ValueError(job.get('detail') or '신규 학습 실패; '+job.get('log',''))
                            break
                        self.cancelled.wait(1)
                    selected=RUNTIME/launched['output'];model=api.model_state(api.source_settings(),selected)
                    if not model['compatible']:raise ValueError('신규 정책 호환성 실패: '+' · '.join(model['reasons']))
                    self.phase(key,title,'complete','별도 정책·Replay 저장 및 호환 확인: '+str(selected))
                else:
                    self.phase(key,title,'complete','기존 정책 사용: '+str(selected))
                    self.phase('train-'+currency,currency+' 신규 SAC 학습','complete','호환 정책 재사용; 신규 학습 생략')
                # Validate official observation/action contracts through the existing loader, no prediction/training here.
                self.interrupted();runtime.check_policy(selected)
                self.phase('policy-'+currency,currency+' SAC 정책 호환성','complete','원본 환경 관측·행동 계약으로 공식 SAC 로딩 확인: '+str(selected))
                ready_policies[currency]=(selected/'sac.zip').relative_to(RUNTIME).as_posix()
            self.interrupted();key='trading';title='실제 입력 추론 · 가상매매';self.phase(key,title)
            if not ready_policies:raise ValueError('준비된 SAC 정책이 없습니다. 통화별 준비 부족 사유를 확인하세요.')
            with runtime.lock:
                self.interrupted()
                atomic_json(ready_policies,ROOT/'runtime/operations/policies.json')
                runtime.command('paper',True);runtime.command('engine',True)
            runtime.sac_decision()
            report=read_json(ROOT/'runtime/experts/status.json')
            failures.extend(expert+': '+str(row.get('reason','Expert 추론 실패')) for expert,row in report.get('experts',{}).items() if expert in catalog.get('active',[]) and row.get('status')!='ready')
            self.phase(key,title,'complete',', '.join(ready_policies)+' 실제 가격·Expert 관측으로 SAC 판단 실행; 이후 완료 바에서 기존 가상체결. 실제 증권 주문 미전송')
            with self.lock:
                self.value.update(status='blocked' if failures else 'complete',detail=' · '.join(failures) if failures else '전체 운영 시작',finished_at=time.time());atomic_json(self.value,self.path)
        except Exception as exc:
            if key=='trading':runtime.command('engine',False);runtime.command('paper',False)
            self.phase(key,title,'blocked' if isinstance(exc,InterruptedError) or isinstance(exc,ValueError) else 'failed',str(exc))
            with self.lock:self.value.update(status='blocked' if isinstance(exc,(InterruptedError,ValueError)) else 'failed',detail=str(exc));atomic_json(self.value,self.path)
        finally:self.active=False
    def stop(self):
        from .operations_runtime import runtime
        from .library_operations import library
        from ..web_api import job_state,stop
        self.cancel();library.cancelled.set();runtime.cancel_inference.set()
        runtime.command('engine',False);runtime.command('paper',False);runtime.command('feed',False)
        if job_state()['running']:stop()
        if runtime.account:runtime.account.save()
        pending=bool(runtime.inference_active or library.active or runtime.thread and runtime.thread.is_alive() or self.active)
        self.phase('stop','전체 시스템 중지','running' if pending else 'complete','현재 추론/수신 작업 종료 대기' if pending else '운영 중지; 서버·모델·계좌 파일 유지')
        self.value.update(status='running' if pending else 'complete',detail='중지 요청 처리',stop_requested=True);atomic_json(self.value,self.path)
        return {'message':'운영 중지 요청을 처리했습니다. 현재 작업 종료 상태는 화면에서 확인하세요.','pending':pending}

system=SystemOperations()
