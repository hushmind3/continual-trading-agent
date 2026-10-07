"""Dedicated PT worker lifecycle. Status reads never import torch or load weights."""
import os
from pathlib import Path
import subprocess
import threading
import time
import psutil
from .resources import ROOT
from ..expert_registry import atomic_json
from ..paths import EXPERT_ASSETS_DIR, TRADING_MOE_CHECKPOINT, default_runtime_dir
from ..state_io import read_json
from ..state_io import rotate_worker_log
from ..state_io import evidence_status


class TradingMoELifecycle:
    def __init__(self,checkpoint=None,state=None):
        self.artifacts=EXPERT_ASSETS_DIR
        self.checkpoint=Path(checkpoint) if checkpoint else TRADING_MOE_CHECKPOINT
        self.state=Path(state) if state else ROOT/"runtime/trading_moe/native_vertical_run"
        self.record=self.state/"worker.json" if state else ROOT/"runtime/trading_moe/worker.json"
        self.lock=threading.RLock()
        self.runner_script="run_native_vertical_trading.py"
        self.extra_args=[]
        self.source_mode='live'
        self.market=default_runtime_dir()/'live'/'market.csv'

    read = staticmethod(read_json)

    def process(self):
        record=self.read(self.record)
        try:
            p=psutil.Process(record["pid"])
            return p if p.is_running() and p.create_time()==record["created"] and p.cmdline()==record["command"] else None
        except (psutil.Error,KeyError):return None

    def status(self):
        with self.lock:
            data=self.read(self.state/"worker_status.json")
            data["cache"] = evidence_status(self.state)
            data.setdefault("source_kind", self.source_mode if self.runner_script == "run_native_vertical_trading.py" else "historical_evaluation")
            process=self.process()
            if process is None:
                previous=data.get("status")
                data["status"]="stopped"
                if previous in ("loading","running","saving"):
                    data["error"]=data.get("error") or "worker가 종료됐습니다. 마지막 저장 상태에서 다시 시작할 수 있습니다."
            elif data.get("pid")!=process.pid:
                # Windows venv's launcher spawns the actual Python worker.
                # Only accept a reported PID in this launcher's process tree.
                try:
                    worker=psutil.Process(int(data.get("pid",0)))
                    if process.pid in [p.pid for p in worker.parents()]:process=worker
                    else:data["status"]="loading"
                except (psutil.Error,ValueError,TypeError):data["status"]="loading"
            data.update(pid=process.pid if process else None,alive=process is not None,
                checkpoint=str(self.checkpoint),paper=True)
            try:data["worker_ram_bytes"]=process.memory_info().rss if process else 0
            except psutil.Error:data["worker_ram_bytes"]=0
            checkpoint=self.checkpoint
            data["checkpoint_bytes"]=checkpoint.stat().st_size if checkpoint.exists() else 0
            if not data.get("books"):
                from ..paper_account import PaperAccount
                account=self.read(self.state/"paper_account.json")
                if account:
                    paper=PaperAccount(self.state/"paper_account.json",.001,.0001)
                    data["books"]=paper.snapshot()["books"]
                    data["reward_points"]=paper.reward_points()
                    data["fills"]=account.get("fills",[])[-20:]
                    report=self.read(self.state/"report.json")
                    data.setdefault("optimizer_updates",report.get("optimizer_updates",0))
            if process and (self.state/"stop.request").exists():data["stop_requested"]=True
            return data

    def start(self,*,recovery=False):
        with self.lock:
            if self.process():return {"ok":True,"already_running":True,"state":self.status()}
            checkpoint=self.checkpoint
            python=self.artifacts/"venv/Scripts/python.exe"
            if not checkpoint.is_file() or not python.is_file():
                return {"ok":False,"error":"TradingMoE.pt 또는 전용 Python 환경을 찾을 수 없습니다."}
            self.state.mkdir(parents=True,exist_ok=True)
            (self.state/"stop.request").unlink(missing_ok=True)
            previous=self.read(self.state/"worker_status.json")
            atomic_json(self.state/"worker_status.json",{**previous,"status":"loading","error":None,"stop_requested":False})
            command=[str(python),"-u",str(ROOT/"scripts"/self.runner_script),
                "--root",str(self.artifacts),"--checkpoint",str(checkpoint),"--state",str(self.state),"--resume","--continuous"]
            command.extend(self.extra_args)
            if self.runner_script=='run_native_vertical_trading.py':
                command.extend(['--mode',self.source_mode,'--market',str(self.market)])
            try:
                rotate_worker_log(self.state/"worker.log")
                with (self.state/"worker.log").open("ab") as log:
                    worker=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
                process=psutil.Process(worker.pid)
                prior=self.read(self.record)
                atomic_json(self.record,{"pid":worker.pid,"created":process.create_time(),"command":process.cmdline(),
                    'requested':True,'restart_attempts':prior.get('restart_attempts',0) if recovery else 0})
                return {"ok":True,"state":self.status()}
            except OSError as exc:
                return {"ok":False,"error":str(exc)}

    def stop(self):
        with self.lock:
            if self.record.is_file():
                record=self.read(self.record);record['requested']=False;atomic_json(self.record,record)
            if not self.process():return {"ok":True,"already_stopped":True,"state":self.status()}
            (self.state/"stop.request").write_text("save and exit",encoding="utf-8")
            return {"ok":True,"message":"현재 사이클 후 계좌·replay·optimizer·PT를 저장하고 종료합니다.","state":self.status()}

    def recover(self):
        """Retry requested live workers with bounded backoff; never restart a trial."""
        with self.lock:
            record=self.read(self.record)
            if not record.get('requested') or self.runner_script=='run_assembly_trial.py':return None
            if (self.state/'stop.request').exists():return None
            if self.process():
                if record.get('restart_attempts') and time.time()-record['created']>=120:
                    record['restart_attempts']=0;atomic_json(self.record,record)
                return None
            from ..operating_rules import operating_rules
            rules=operating_rules();attempts=record.get('restart_attempts',0)
            if attempts>=rules['runtime_restart_attempts']:
                record['requested']=False;atomic_json(self.record,record)
                status=self.read(self.state/'worker_status.json')
                status.update(status='error',error='자동 복원 시도 한도 도달 · 원인 확인 후 다시 시작하세요.')
                atomic_json(self.state/'worker_status.json',status)
                return {'ok':False,'exhausted':True}
            if 'retry_at' not in record:
                record['retry_at']=time.time()+rules['runtime_restart_base_seconds']*2**attempts
                atomic_json(self.record,record);return None
            if time.time()<record['retry_at']:return None
            record['restart_attempts']=attempts+1;record.pop('retry_at',None);atomic_json(self.record,record)
            return self.start(recovery=True)
