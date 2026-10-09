"""Process identity, bounded restarts and graceful persistence for the portfolio service."""
from __future__ import annotations

import os
import subprocess
import sys
import shutil
import threading
import time
from pathlib import Path
import psutil
from apscheduler.schedulers.background import BackgroundScheduler
from ..paths import PROJECT_ROOT
from ..state_io import atomic_json,read_json
from ..provider_credentials import public_status
from .config import load_settings,CONFIG_PATH
from .journal import Journal
from .checkpoint import Checkpoints
from .resources import ResourceMonitor
from .data_universe import prepare
from .training_status import readiness
from .library_operations import LibraryOperations,ONLINE_LIBRARY_JOBS

MODULES={role:'stockrl.platform.moe_worker' for role in ('experts','agent','learner')}


def terminate_tree(process):
    try:
        for child in reversed(process.children(recursive=True)):
            try:child.terminate()
            except psutil.NoSuchProcess:pass
        process.terminate()
    except psutil.NoSuchProcess:pass


class Runtime:
    def __init__(self,config=CONFIG_PATH):
        self.config=Path(config).resolve(); self.settings=load_settings(self.config)
        self.root=self.settings.state_dir; (self.root/"workers").mkdir(exist_ok=True)
        self.journal=Journal(self.root/"operations.sqlite3",self.settings.resources.journal_limit_mib,self.settings.resources.retained_transitions)
        account=self.journal.get_state('account')
        if account:self.journal.record_fills(account.get('fills',[]),account['books'])
        self.checkpoints=Checkpoints(self.root/"policies",self.settings.resources.revisions)
        self.resources=ResourceMonitor(self.root)
        self.input_config=prepare(self.settings)
        self.lock=threading.RLock(); self.closing=threading.Event(); self.children={}; self.handles={}; self.retries={}
        self.controls=read_json(self.root/"control.json") or {"feed":False,"engine":False,"paper":False,"learning":True,"mode":"live"}
        self.library=LibraryOperations(self)
        from .progress_status import ProgressTracker
        self.progress=ProgressTracker()
        atomic_json(self.controls,self.root/"control.json")
        self.scheduler=BackgroundScheduler(job_defaults={"max_instances":1,"coalesce":True})
        self.scheduler.add_job(self._monitor,"interval",seconds=1,misfire_grace_time=10,id="workers")
        self.scheduler.start()

    def wanted(self,role):
        return bool(self.controls["feed"] if role=="feed" else self.controls["engine"] and (role!="learner" or self.controls["learning"]))

    def process(self,role):
        owner=role if role=='feed' else 'agent'
        record=read_json(self.root/"workers"/(owner+".pid.json"))
        state=read_json(self.root/'workers'/(role+'.json'))
        expected=str(self.root/'live'/'market.csv') if role=='feed' else str(self.config)
        tag='stockrl' if role=='feed' else MODULES[role]
        def matches(process):
            cmd=' '.join(process.cmdline())
            return expected in cmd and tag in cmd and process.is_running()
        try:
            process=psutil.Process(record["pid"])
            if abs(process.create_time()-record["created_at"])>.02:
                return None
            if not matches(process):return None
            # Windows venv python.exe may be a redirector. Resource/control ownership belongs to the actual interpreter.
            children=[p for p in process.children(recursive=True) if matches(p)]
            return next((p for p in children if p.pid==state.get('pid')),children[-1] if children else process)
        except (KeyError,psutil.Error):
            try:
                process=psutil.Process(state['pid'])
                return process if abs(process.create_time()-state['created_at'])<.02 and matches(process) else None
            except (KeyError,psutil.Error):return None

    def spawn(self,role):
        for stage in ('experts','agent','learner') if role=='agent' else (role,):
            (self.root/"workers"/(stage+".stop")).unlink(missing_ok=True)
            atomic_json({"status":"starting","error":None},self.root/"workers"/(stage+".json"))
        if role=="feed":
            self.input_config=prepare(self.settings)
            args=[sys.executable,"-m","stockrl.platform.feed_worker","--config",str(self.config),
                  "--source",str(self.input_config),"--output",str(self.root/"live"/"market.csv")]
        else:
            args=[sys.executable,"-m",MODULES[role],"--config",str(self.config)]
        env=os.environ.copy(); env["PYTHONPATH"]=str(PROJECT_ROOT/"src"); env["PYTHONUTF8"]="1"
        log=self.root/"workers"/(role+".log")
        if log.exists() and log.stat().st_size>2*1024*1024:
            log.write_text('',encoding="utf-8")
        old=self.handles.pop(role,None)
        if old: old.close()
        handle=log.open('a',encoding="utf-8"); self.handles[role]=handle
        atomic_json({"status":"starting","error":None},self.root/"workers"/(role+".json"))
        child=subprocess.Popen(args,cwd=PROJECT_ROOT,env=env,stdout=handle,stderr=subprocess.STDOUT,
                               creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        self.children[role]=child
        process=psutil.Process(child.pid)
        atomic_json(dict(pid=child.pid,created_at=process.create_time()),self.root/"workers"/(role+".pid.json"))

    def _monitor(self):
        if self.closing.is_set():return
        with self.lock:
            if shutil.disk_usage(self.root).free < self.settings.resources.disk_reserve_gib*2**30:
                if self.controls.get('paper') or self.controls.get('feed'):
                    self.journal.event('error','디스크 여유 공간이 운영 기준보다 작습니다. 시세·체결·학습을 정지했습니다.')
                    self.controls.update(feed=False,paper=False,learning=False)
                    atomic_json(self.controls,self.root/'control.json')
            for role in ("feed","agent"):
                process=self.process(role)
                if not self.wanted(role):
                    if process: (self.root/"workers"/(role+".stop")).touch()
                    self.children.pop(role,None)
                    self.retries.pop(role,None)
                    continue
                if process:
                    state=read_json(self.root/"workers"/(role+".json"))
                    expert_state=read_json(self.root/'workers'/'experts.json') if role=='agent' else {}
                    if expert_state.get("status")=="inference" and time.time()-expert_state.get("active_since",time.time())>self.settings.resources.inference_timeout_seconds:
                        self.journal.event("error","Expert 추론 시간 제한을 넘었습니다. 프로세스를 복구합니다.")
                        terminate_tree(process)
                    continue
                attempt,next_try=self.retries.get(role,(0,0))
                if attempt>=5 or time.time()<next_try:
                    continue
                if role in self.children:
                    intentional=read_json(self.root/'workers'/(role+'.json')).get('reason')=='configuration_changed'
                    if not intentional:self.journal.event("error",f"{role} 프로세스가 종료되었습니다. 재시도 {attempt+1}/5")
                    else:attempt=0
                try:
                    self.spawn(role)
                    self.retries[role]=(attempt+1,time.time()+min(60,2**attempt))
                except Exception as exc:
                    self.journal.event("error",f"{role} 시작 실패: {exc}")
                    self.retries[role]=(attempt+1,time.time()+min(60,2**attempt))

    def command(self,name,enabled,internal=False):
        if name not in ("feed","engine","paper","learning"):
            raise ValueError("지원하지 않는 운영 명령입니다.")
        with self.lock:
            if self.library.active and not internal and self.library.snapshot()['job'].get('kind') not in ONLINE_LIBRARY_JOBS:
                raise ValueError('Expert 구성을 변경 중입니다. 완료 후 조작하세요.')
            if name=="paper" and enabled and not self.controls.get("engine"):
                raise ValueError("MoE 실행을 먼저 시작하세요.")
            self.controls[name]=bool(enabled)
            if name=="engine" and not enabled:
                self.controls["paper"]=False
            if enabled:
                roles={"feed":("feed",),"engine":("experts","agent","learner"),"learning":("learner",),"paper":()}
                for role in roles[name]:
                    self.retries.pop(role,None)
            atomic_json(self.controls,self.root/"control.json")
        return dict(accepted=True,controls=self.controls.copy())

    def snapshot(self):
        workers={}
        for role in ("feed","experts","agent","learner"):
            state=read_json(self.root/"workers"/(role+".json"))
            process=self.process(role)
            workers[role]={**state,"alive":bool(process),"pid":process.pid if process else None,
                           "requested":self.wanted(role),"retries":self.retries.get(role,(0,0))[0]}
        agent=workers["agent"]; expert=workers["experts"]; learner=workers["learner"]
        feed=read_json(self.root/"live"/"live_feed_metrics.json")
        replay=learner.get("replay") or self.journal.stats(agent.get("rollout_generation",agent.get("version",0)),0)
        training=readiness(self.controls,workers,replay,self.settings.learning)
        if self.library.active and self.library.snapshot()['job'].get('kind') not in ONLINE_LIBRARY_JOBS:
            training.update(code='composition',label='Expert 구성 적용 중',detail=self.library.snapshot()['job'].get('detail','학습 상태를 이어받는 중'),action=None)
        result=dict(architecture="finrlx-unified-gpu-moe-v1",controls=self.controls.copy(),workers=workers,feed=feed,
                    agent=agent,experts=expert.get("experts",[]),learner=learner,
                    account=self.journal.get_state("account"),decisions=self.journal.get_state("decisions") or [],
                    replay=replay,training=training,
                    resources=self.resources.snapshot(workers),events=self.journal.events(),provider=public_status(self.root),
                    revisions=self.checkpoints.revisions(),settings=self.settings.model_dump(),real_orders_enabled=False,
                    current_policy=read_json(self.checkpoints.root/'current.json'),
                    library=self.library.snapshot(),time=time.time())
        actual=self.journal.get_state('learning_metrics') or {}
        row=self.journal.db.execute("SELECT created,detail FROM events WHERE kind='learning' ORDER BY id DESC LIMIT 1").fetchone()
        result['last_learning']=dict(time=actual.get('updated_at') or (row[0] if row else None),detail=row[1] if row else None,measurement=actual or None)
        result['progress']=self.progress.snapshot(result)
        return result

    def shutdown(self):
        self.closing.set(); self.scheduler.shutdown(wait=True)
        if self.library.child and self.library.child.poll() is None:
            terminate_tree(psutil.Process(self.library.child.pid))
        processes=[]
        for role in ("feed","agent"):
            process=self.process(role)
            if process:
                (self.root/"workers"/(role+".stop")).touch(); processes.append(process)
        _,alive=psutil.wait_procs(processes,timeout=30)
        for process in alive:
            terminate_tree(process)
        for handle in self.handles.values(): handle.close()
        self.journal.close()
