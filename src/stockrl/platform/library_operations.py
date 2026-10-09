"""Responsive operations API; model work runs in one bounded, disposable process."""
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from ..paths import PROJECT_ROOT
from ..state_io import atomic_json,read_json

ONLINE_LIBRARY_JOBS=('inspect','import','probe','probe_all','compare','convert','search','acquire','optimize')


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
            operation=self._hot_apply if kind=='apply' and self._can_hot_apply(payload) else self._run
            threading.Thread(target=operation,args=(kind,payload),name='expert-library-operation',daemon=True).start()
        return self.snapshot()

    def _can_hot_apply(self,payload):
        rt=self.runtime;catalog=read_json(self.catalog_path);installed=catalog.get('installed',{})
        return (rt.controls['engine'] and rt.controls['learning'] and rt.process('agent') and rt.process('learner')
            and all(k in installed and catalog.get('experts',{}).get(k,{}).get('package',{}).get('sha256')==installed[k]
                    for k in payload.get('active',[])))

    def _hot_apply(self,kind,payload):
        try:
            catalog=read_json(self.catalog_path);active=sorted(set(payload.get('active',[])))
            for key in active:
                item=catalog['experts'][key]
                if item['check'].get('status')!='passed' or item['check'].get('package_sha256')!=item['package']['sha256'] or (item.get('conversion') and item['conversion'].get('validation',{}).get('passed') is not True):
                    raise ValueError('실제 추론 검사를 먼저 통과해야 합니다: '+item['name'])
            revision=catalog.get('selection_revision',0)+1
            atomic_json(dict(stage='checkpoint_requested',kind=kind,selection_revision=revision,
                detail='실행은 유지하며 슬롯 선택과 학습 체크포인트를 적용 중'),self.status_path)
            atomic_json({**catalog,'active':active,'selection_revision':revision},self.catalog_path)
            self.runtime.settings.enabled_experts=active
            atomic_json(self.runtime.settings.model_dump(),self.runtime.config)
            deadline=time.monotonic()+20
            while read_json(self.status_path).get('stage')!='complete':
                if time.monotonic()>deadline:raise TimeoutError('선택은 저장됐지만 학습기 확인이 지연됐습니다. 프로세스 상태를 확인하세요.')
                time.sleep(.2)
        except Exception as exc:
            atomic_json(dict(stage='error',kind=kind,error=str(exc)),self.status_path)
        finally:self.active=False

    def _pause(self,kind):
        rt=self.runtime;rt.command('engine',False,internal=True)
        atomic_json(dict(stage='pausing',kind=kind,detail='학습 상태를 저장하고 구성 변경 준비'),self.status_path)
        deadline=time.monotonic()+30
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
            if kind=='optimize' and result and result.get('target_active'):
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
