"""Optional FinRL-Trading integrations."""
import importlib
import sys
import threading
from pathlib import Path
SOURCE_ROOT=Path(__file__).resolve().parent/"upstream"

_module_lock=threading.RLock()

def finrlx(name):
    source=SOURCE_ROOT
    with _module_lock:
        if str(source) not in sys.path:sys.path.insert(0,str(source))
        return importlib.import_module('src.'+name)
