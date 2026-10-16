"""Low-frequency API recovery; never starts finance operations or agent jobs."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

from start_server import ROOT,RUNTIME,PORT,ready,listeners,main,blockers
from platform_modules import signature
from stockrl.state_io import read_json,atomic_json

STATUS=RUNTIME/'server-watchdog.json'
STOP=RUNTIME/'server-watchdog.stop'


def running():
    record=read_json(STATUS)
    if record.get('status')!='running':return False
    try:
        process=psutil.Process(int(record['pid']))
        return (abs(process.create_time()-record['process_created'])<.01
            and Path(process.cwd()).resolve()==ROOT
            and any(Path(arg).resolve()==Path(__file__).resolve() for arg in process.cmdline()[1:]))
    except (KeyError,ValueError,OSError,psutil.Error):return False


def recover():
    if ready():return False
    # A busy/unresponsive listener or somebody else's service is never killed.
    if listeners(PORT):return False
    main(apply_only=True,skip_build=True,skip_checks=True,watchdog=False)
    if not ready():raise RuntimeError('서버 복구 후 API 응답 없음')
    return True


def supervise():
    import msvcrt
    RUNTIME.mkdir(parents=True,exist_ok=True)
    with (RUNTIME/'server-watchdog.lock').open('a+b') as lock:
        if lock.tell()==0:lock.write(b'.');lock.flush()
        lock.seek(0)
        try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:return
        record={'pid':os.getpid(),'process_created':psutil.Process().create_time(),
            'status':'running','started_at':time.time(),'restarts':0,'last_error':'',
            'module_watch_version':1,'modules_signature':signature()}
        atomic_json(record,STATUS)
        try:
            while not STOP.exists():
                delay=5
                try:
                    if recover():
                        record.update(restarts=record['restarts']+1,last_restart_at=time.time(),last_error='')
                        atomic_json(record,STATUS)
                    elif (desired:=signature())!=record['modules_signature']:
                        active=blockers()
                        if active:
                            record.update(modules_pending=desired,modules_blockers=active)
                            atomic_json(record,STATUS)
                        else:
                            # Import preflight precedes build/restart; a bad plugin leaves the live host intact.
                            with (RUNTIME/'module-preflight.log').open('w',encoding='utf8') as output:
                                env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'backend')
                                subprocess.run([sys.executable,'-X','utf8','-B','-c','import web_api'],cwd=ROOT/'backend',env=env,stdout=output,stderr=subprocess.STDOUT,check=True,timeout=90)
                            main(apply_only=True,skip_build=False,skip_checks=True,watchdog=False)
                            if not ready():raise RuntimeError('모듈 적용 후 API 응답 없음')
                            record.update(modules_signature=desired,modules_applied_at=time.time(),modules_pending='',modules_blockers=[],last_error='')
                            atomic_json(record,STATUS)
                    elif record['last_error']:
                        record['last_error']='';atomic_json(record,STATUS)
                except Exception as exc:
                    record.update(last_error=str(exc),last_error_at=time.time())
                    atomic_json(record,STATUS)
                    print(f'API recovery failed: {exc}',flush=True)
                    delay=60
                # Allow an explicit stop even during failure backoff.
                for _ in range(delay):
                    if STOP.exists():break
                    time.sleep(1)
        finally:
            record.update(status='stopped',stopped_at=time.time());atomic_json(record,STATUS)
            lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)


if __name__=='__main__':supervise()
