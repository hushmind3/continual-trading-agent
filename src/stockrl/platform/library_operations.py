"""Responsive operations API; model work runs in one bounded, disposable process."""
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from ..paths import PROJECT_ROOT
from ..state_io import atomic_json,read_json

ONLINE_LIBRARY_JOBS=('inspect','import','probe','probe_all','compare','convert','search','acquire','optimize','optimize_all')


class LibraryOperations:
    def __init__(self,runtime):
        self.runtime=runtime;self.lock=threading.Lock();self.active=False;self.child=None
        self.status_path=runtime.root/'library-job.json'
        self.catalog_path=runtime.root/'expert-library.json'

    def snapshot(self):
        return dict(catalog=read_json(self.catalog_path),job={**read_json(self.status_path),'busy':self.active})

    def start(self,kind,payload):
        if kind not in ('prepare','apply','delete',*ONLINE_LIBRARY_JOBS):raise ValueError('지원하지 않는 라이브러리 작업')
        if kind=='apply' and (not isinstance(payload.get('active'),list) or not all(isinstance(k,str) for k in payload['active'])):
            raise ValueError('사용할 Expert 슬롯 목록을 지정하세요.')
        with self.lock:
            if self.active:raise ValueError('진행 중인 Expert 작업이 있습니다.')
            self.active=True
            atomic_json(dict(stage='queued',kind=kind,started=time.time()),self.status_path)
            threading.Thread(target=self._run,args=(kind,payload),name='expert-library-operation',daemon=True).start()
        return self.snapshot()

    def _pause(self,kind):
        rt=self.runtime;rt.command('engine',False,internal=True)
        atomic_json(dict(stage='pausing',kind=kind,detail='학습 상태를 저장하고 구성 변경 준비'),self.status_path)
        deadline=time.monotonic()+rt.settings.resources.inference_timeout_seconds+30
        while any(rt.process(role) for role in ('agent','learner','experts')):
            if time.monotonic()>deadline:raise TimeoutError('추론·학습 정지가 완료되지 않았습니다.')
            time.sleep(.25)

    def _execute(self,kind,payload,request):
        rt=self.runtime;atomic_json(dict(kind=kind,payload=payload),request)
        env=os.environ.copy();env.update(PYTHONPATH=str(PROJECT_ROOT/'src'),PYTHONUTF8='1')
        self.child=subprocess.Popen([sys.executable,'-m','stockrl.platform.library_worker','--config',str(rt.config),
            '--request',str(request)],cwd=PROJECT_ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.child.wait(timeout=1800)
        if self.child.returncode:raise RuntimeError(read_json(self.status_path).get('error','Expert 작업 프로세스가 종료됐습니다.'))
        return read_json(self.status_path).get('result')

    def _run(self,kind,payload):
        rt=self.runtime;before=rt.controls.copy()
        paused=kind not in ONLINE_LIBRARY_JOBS or not read_json(self.catalog_path).get('installed')
        request=rt.root/'library-request.json'
        try:
            if paused:self._pause(kind)
            result=self._execute(kind,payload,request)
            if kind in ('acquire','import') and result and result.get('check',{}).get('status')=='passed' and payload.get('activate',True):
                catalog=read_json(self.catalog_path);base=(result.get('conversion') or {}).get('source_id',result['id'])
                family=[k for k,v in catalog['experts'].items() if k==base or (v.get('conversion') or {}).get('source_id')==base]
                active=[k for k in catalog.get('active',[]) if k not in family]+[result['id']]
                before=rt.controls.copy();paused=True;self._pause('apply')
                self._execute('apply',dict(active=active,admission_id=result['id']),request)
            if kind in ('optimize','optimize_all') and result and result.get('target_active') is not None:
                before=rt.controls.copy();paused=True;self._pause('apply')
                self._execute('apply',dict(active=result['target_active'],optimizer_base=result['base']),request)
            rt.settings=__import__('stockrl.platform.config',fromlist=['load_settings']).load_settings(rt.config)
            from .data_universe import prepare
            rt.input_config=prepare(rt.settings)
        except Exception as exc:
            atomic_json(dict(stage='error',kind=kind,error=str(exc),finished=time.time()),self.status_path)
        finally:
            if self.child is not None and self.child.poll() is None:
                from .runtime import terminate_tree
                import psutil
                terminate_tree(psutil.Process(self.child.pid))
            self.child=None;request.unlink(missing_ok=True)
            if paused and not rt.closing.is_set():
                rt.command('engine',before['engine'],internal=True)
                if before['engine'] and before['paper']:rt.command('paper',True,internal=True)
            self.active=False
