"""Measured system/process pressure; weight sizes are not resource usage metrics."""
import shutil
import subprocess
import time
from pathlib import Path
import psutil


class ResourceMonitor:
    def __init__(self, root):
        self.root=Path(root); self.processes={}; self.gpu={}; self.gpu_sample=0
        psutil.cpu_percent(None)

    def snapshot(self, workers):
        memory=psutil.virtual_memory()
        rows=[]
        for role,record in workers.items():
            pid=record.get("pid")
            if not pid or not record.get("alive"):
                continue
            try:
                process=self.processes.setdefault(pid,psutil.Process(pid))
                io=process.io_counters(); mem=process.memory_info()
                rows.append(dict(role=role,pid=pid,rss_bytes=mem.rss,cpu_percent=process.cpu_percent(None),
                                 threads=process.num_threads(),read_bytes=io.read_bytes,write_bytes=io.write_bytes))
            except psutil.Error:
                pass
        alive={r["pid"] for r in rows}; self.processes={k:p for k,p in self.processes.items() if k in alive}
        if time.monotonic()-self.gpu_sample>5:
            command=shutil.which("nvidia-smi")
            if not command:
                command=next((str(p) for p in [Path('C:/Windows/System32/nvidia-smi.exe'),Path('C:/Program Files/NVIDIA Corporation/NVSMI/nvidia-smi.exe')] if p.exists()),None)
            if command:
                try:
                    result=subprocess.run([command,"--query-gpu=name,utilization.gpu,memory.used,memory.total","--format=csv,noheader,nounits"],
                                          capture_output=True,text=True,timeout=2,check=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                    name,util,used,total=result.stdout.splitlines()[0].split(',')
                    self.gpu=dict(name=name.strip(),utilization_percent=float(util),used_bytes=float(used)*2**20,total_bytes=float(total)*2**20)
                except (ValueError,OSError,subprocess.SubprocessError):
                    self.gpu={"error":"GPU 측정 실패"}
            self.gpu_sample=time.monotonic()
        disk=shutil.disk_usage(self.root)
        return dict(cpu_percent=psutil.cpu_percent(None),ram_total_bytes=memory.total,ram_available_bytes=memory.available,
                    ram_used_bytes=memory.total-memory.available,gpu=self.gpu,disk_free_bytes=disk.free,processes=rows)
