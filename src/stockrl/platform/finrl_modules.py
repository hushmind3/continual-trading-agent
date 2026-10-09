"""Load the installed FinRL-X modules, including their upstream src.* imports."""
import importlib
import sys
import types


def module(name):
    if 'src' not in sys.modules:
        namespace=types.ModuleType('src');namespace.__path__=[];sys.modules['src']=namespace
    for package in ('data','config'):
        sys.modules.setdefault('src.'+package,importlib.import_module(package))
    return importlib.import_module(name)


def __getattr__(name):
    sources={'DataStore':'data.data_store','DataProcessor':'data.data_processor',
        'BacktestEngine':'backtest.backtest_engine','BacktestConfig':'backtest.backtest_engine'}
    if name not in sources:raise AttributeError(name)
    value=getattr(module(sources[name]),name)
    globals()[name]=value
    return value
