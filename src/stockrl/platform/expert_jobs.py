"""Sequential heavy-Expert admission, progress and process-tree cleanup."""
import os
import subprocess
import sys
import time
from datetime import date,datetime
import psutil
from ..paths import PROJECT_ROOT
from ..state_io import atomic_json,read_json
from .config import CONFIG_PATH
from .worker_state import publish,stopped


def json_scalar(value):
    if isinstance(value,(date,datetime)):return value.isoformat()
    if hasattr(value,'item'):return value.item()
    raise TypeError(f'지원하지 않는 Expert 입력 형식: {type(value).__name__}')


def terminate(process):
    try:
        descendants=psutil.Process(process.pid).children(recursive=True)
        for child in reversed(descendants):
            try:child.terminate()
            except psutil.NoSuchProcess:pass
        process.terminate();process.wait(timeout=10)
        psutil.wait_procs(descendants,timeout=10)
    except (psutil.NoSuchProcess,ProcessLookupError):pass


def run_job(settings,key,batches,metrics,config=CONFIG_PATH):
    path=settings.state_dir/'workers'/'expert-job.json'
    result=path.with_suffix('.result.json');progress=path.with_suffix('.progress.json')
    for file in (result,progress):file.unlink(missing_ok=True)
    atomic_json({'key':key,'batches':batches,'metrics':metrics.get(key,{})},path,default=json_scalar)
    env=os.environ.copy();env['PYTHONPATH']=str(PROJECT_ROOT/'src');env['PYTHONUTF8']='1'
    log=settings.state_dir/'workers'/'expert-task.log'
    if log.exists() and log.stat().st_size>2*1024*1024:log.write_text('',encoding='utf-8')
    started=time.monotonic();child=None
    try:
        with log.open('a',encoding='utf-8') as output:
            child=subprocess.Popen([sys.executable,'-m','stockrl.platform.expert_task','--config',str(config),'--job',str(path)],
                cwd=PROJECT_ROOT,env=env,stdout=output,stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            while child.poll() is None:
                if stopped(settings,'experts'):
                    terminate(child);raise InterruptedError('Expert 정지 요청')
                if time.monotonic()-started>settings.resources.inference_timeout_seconds:
                    terminate(child);raise TimeoutError(f'{key}: 전체 분석 시간 제한 초과')
                status=read_json(progress)
                publish(settings,'experts',status='inference',active_expert=key,task_pid=status.get('pid',child.pid),
                        batch=status.get('batch',0),batches=len(batches),active_since=time.time())
                time.sleep(.5)
        response=read_json(result)
        if response.get('error'):
            metrics.setdefault(key,{}).update(status=response['status'],error=response['error'],loaded=False)
            if response['status']=='waiting_resources':raise MemoryError(response['error'])
            if response['status']=='needs_input':raise ValueError(response['error'])
            raise RuntimeError(response['error'])
        if child.returncode or 'packets' not in response:raise RuntimeError(f'{key}: 분석 프로세스 종료 {child.returncode}')
        metrics[key]={**response['metrics'],'loaded':False,'job_seconds':time.monotonic()-started}
        return response['packets']
    finally:
        if child is not None and child.poll() is None:terminate(child)
        for file in (path,result,progress):file.unlink(missing_ok=True)
        publish(settings,'experts',task_pid=None)
