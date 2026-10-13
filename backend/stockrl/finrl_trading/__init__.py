"""FinRL-Trading import boundary for price, provider and native tool integrations."""
import importlib
import sys
import threading
from .. import ROOT

_module_lock=threading.RLock()

def finrlx(name):
    source=ROOT/'backend/stockrl/finrl_trading/library/finrl_x'
    with _module_lock:
        for path in (source/'src',source):
            if str(path) not in sys.path:sys.path.insert(0,str(path))
        return importlib.import_module('src.'+name)
