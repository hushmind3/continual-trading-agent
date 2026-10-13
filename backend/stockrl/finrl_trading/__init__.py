"""Optional FinRL-Trading integrations."""
import importlib
import sys
import threading
from .. import ROOT

_module_lock=threading.RLock()

def finrlx(name):
    source=ROOT/'vendor/FinRL-X'
    with _module_lock:
        for path in (source/'src',source):
            if str(path) not in sys.path:sys.path.insert(0,str(path))
        return importlib.import_module('src.'+name)
