"""Optional FinRL-Trading integrations."""
import importlib
import sys
import threading
from .. import ROOT

_module_lock=threading.RLock()

def finrlx(name):
    source=ROOT/'FinRL-X'
    with _module_lock:
        if str(source) not in sys.path:sys.path.insert(0,str(source))
        return importlib.import_module('src.'+name)
