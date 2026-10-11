"""Timestamp and JSON compatibility for frozen native runner definitions."""
from datetime import datetime,timezone
from .state_io import atomic_json as _write

def utc_now():return datetime.now(timezone.utc).isoformat()
def atomic_json(path,value):_write(value,path)
