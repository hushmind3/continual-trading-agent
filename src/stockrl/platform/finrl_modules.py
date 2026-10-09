"""Load the installed FinRL-X modules, including their upstream src.* imports."""
import importlib
import sys
import types


def module(name):
    if 'src' not in sys.modules:
        namespace=types.ModuleType('src');namespace.__path__=[];sys.modules['src']=namespace
    for package in ('data','config','trading'):
        sys.modules.setdefault('src.'+package,importlib.import_module(package))
    return importlib.import_module(name)


def __getattr__(name):
    if name=='StockTradingEnv':
        # Load the installed official environment without FinRL's eager imports
        # of unrelated crypto brokers, data providers and every agent package.
        from pathlib import Path
        import importlib.util
        package=importlib.util.find_spec('finrl')
        path=Path(package.origin).parent/'meta/env_stock_trading/env_stocktrading.py'
        spec=importlib.util.spec_from_file_location('finrl_stock_env',path)
        loaded=importlib.util.module_from_spec(spec);sys.modules[spec.name]=loaded
        spec.loader.exec_module(loaded)
        globals()[name]=loaded.StockTradingEnv
        return loaded.StockTradingEnv
    sources={'DataStore':'data.data_store','DataProcessor':'data.data_processor',
        'BacktestEngine':'backtest.backtest_engine','BacktestConfig':'backtest.backtest_engine',
        'TradeExecutor':'trading.trade_executor','ExecutionConfig':'trading.trade_executor',
        'OrderResponse':'trading.alpaca_manager','calculate_returns':'trading.performance_analyzer'}
    if name not in sources:raise AttributeError(name)
    if sources[name]=='trading.trade_executor':
        sys.modules.setdefault('alpaca_manager',module('trading.alpaca_manager'))
    value=getattr(module(sources[name]),name)
    globals()[name]=value
    return value
