"""Live inference precedes queued learning; each priority retains FIFO order."""
from collections import deque
from contextlib import contextmanager
import threading
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import psutil


class FairGpuScheduler:
    def __init__(self,preopen_learning=False,clock=None):
        self.condition=threading.Condition()
        self.queue=deque()
        self.active=None
        self.last={}
        self.preopen_learning=preopen_learning
        self.clock=clock or (lambda:datetime.now(timezone.utc))

    def learning_first(self):
        now=self.clock()
        korea=now.astimezone(ZoneInfo("Asia/Seoul"))
        new_york=now.astimezone(ZoneInfo("America/New_York"))
        return self.preopen_learning and korea.hour>=20 and (new_york.hour,new_york.minute)<(9,30)

    def priority(self,role):
        if self.learning_first():
            if "_learning_" in role:
                return 0
            if role=="candidate_publish":
                return 1
            return 3 if role.startswith("validation_") else 2
        if role in ("champion_live","candidate_live"):
            return 0
        if role=="candidate_publish":
            return 1
        if role.startswith("validation_"):
            return 2
        return 3

    def next_request(self):
        return min(self.queue,key=lambda item:(self.priority(item[1]),item[2]))

    @contextmanager
    def work(self,role):
        token=object();requested=time.perf_counter()
        with self.condition:
            self.queue.append((token,role,requested))
            self.condition.notify_all()
            self.condition.wait_for(lambda:self.active is None and self.next_request()[0] is token)
            self.queue.remove((token,role,requested))
            started=time.perf_counter()
            self.active=(token,role,started)
        try:
            yield
        finally:
            finished=time.perf_counter()
            with self.condition:
                self.last[role]={"wait_seconds":started-requested,
                                 "work_seconds":finished-started}
                self.active=None
                self.condition.notify_all()

    def snapshot(self):
        with self.condition:
            now=time.perf_counter()
            now_utc=self.clock()
            market_open=now_utc.astimezone(ZoneInfo("America/New_York")).replace(hour=9,minute=30,second=0,microsecond=0)
            return {"policy":("preopen_replay_learning_first" if self.learning_first()
                    else "live_inference_first_then_publish_validation_learning"),
                "learning_priority_until_utc":market_open.astimezone(timezone.utc).isoformat() if self.learning_first() else None,
                "active":self.active[1] if self.active else None,
                "active_seconds":now-self.active[2] if self.active else 0,
                "waiting":[{"role":role,"wait_seconds":now-requested}
                           for _,role,requested in sorted(self.queue,key=lambda item:(self.priority(item[1]),item[2]))],
                "last":{role:dict(data) for role,data in self.last.items()}}


class ResourceMonitor:
    """Bounded measurements and admission using observed runtime footprints."""
    def __init__(self):
        from .operating_rules import operating_rules
        self.process=psutil.Process()
        self.measurements={}
        self.reserve_mib=int(operating_rules()['native_vram_reserve_mib'])
        self.process.cpu_percent(None)

    def native_device(self,expert,requested,reserve_mib=None):
        import torch
        previous=self.measurements.get('expert:'+expert,{})
        if psutil.virtual_memory().available < max(64*1024**2,previous.get('rss_growth_bytes',0)):
            raise MemoryError('available RAM is below observed native execution footprint')
        if requested.startswith('cuda'):
            free,_=torch.cuda.mem_get_info(requested)
            required=previous.get('vram_growth_bytes',0)+(self.reserve_mib if reserve_mib is None else reserve_mib)*1024**2
            if free<required:return 'cpu'
        return requested

    @contextmanager
    def measure(self,name,device='cpu'):
        import torch
        start=time.perf_counter();rss=self.process.memory_info().rss
        cpu=self.process.cpu_times();io=self.process.io_counters()
        cuda=device.startswith('cuda') and torch.cuda.is_available()
        allocated=torch.cuda.memory_allocated(device) if cuda else 0
        if cuda:torch.cuda.reset_peak_memory_stats(device)
        try:yield
        finally:
            current_cpu=self.process.cpu_times();current_io=self.process.io_counters()
            delta=max(0,self.process.memory_info().rss-rss)
            gpu_delta=max(0,torch.cuda.max_memory_allocated(device)-allocated) if cuda else 0
            old=self.measurements.get(name,{})
            self.measurements[name]=dict(seconds=time.perf_counter()-start,device=device,
                runs=old.get('runs',0)+1,rss_growth_bytes=max(delta,old.get('rss_growth_bytes',0)),
                vram_growth_bytes=max(gpu_delta,old.get('vram_growth_bytes',0)),
                cpu_seconds=current_cpu.user+current_cpu.system-cpu.user-cpu.system,
                read_bytes=current_io.read_bytes-io.read_bytes,write_bytes=current_io.write_bytes-io.write_bytes)
            if len(self.measurements)>64:self.measurements.pop(next(iter(self.measurements)))

    def snapshot(self):
        import torch
        memory=self.process.memory_info();io=self.process.io_counters()
        result=dict(available_ram_bytes=psutil.virtual_memory().available,rss_bytes=memory.rss,
            peak_rss_bytes=getattr(memory,'peak_wset',memory.rss),cpu_percent=self.process.cpu_percent(None),
            threads=self.process.num_threads(),read_bytes=io.read_bytes,write_bytes=io.write_bytes,
            measurements=dict(self.measurements))
        if torch.cuda.is_initialized():
            free,total=torch.cuda.mem_get_info()
            result['gpu']=dict(free_bytes=free,total_bytes=total,allocated_bytes=torch.cuda.memory_allocated(),
                reserved_bytes=torch.cuda.memory_reserved(),peak_allocated_bytes=torch.cuda.max_memory_allocated())
        return result
