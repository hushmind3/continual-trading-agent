import os
import time
import psutil
from ..state_io import atomic_json, read_json


def control(settings):
    return read_json(settings.state_dir/"control.json") or {"paper": False, "learning": True}


def stopped(settings, role):
    return (settings.state_dir/"workers"/(role+".stop")).exists()


def publish(settings, role, **changes):
    path = settings.state_dir/"workers"/(role+".json")
    old = read_json(path)
    if changes.get('status')!='error' and 'error' not in changes:
        old.pop('error',None)
    process = psutil.Process()
    old.update(changes, pid=os.getpid(), created_at=process.create_time(), heartbeat=time.time(),
               rss_bytes=process.memory_info().rss, peak_ram_bytes=getattr(process.memory_info(),"peak_wset",process.memory_info().rss))
    atomic_json(old,path)
    return old
