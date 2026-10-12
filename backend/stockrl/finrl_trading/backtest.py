"""Supplementary weighted backtest evaluation."""
from . import finrlx


def evaluate_weights(frame,weights,dates,strategy_name):
    result=finrlx('strategies.base_strategy').StrategyResult(strategy_name,weights)
    module=finrlx('backtest.backtest_engine')
    config=module.BacktestConfig(str(frame.date.min().date()),str(frame.date.max().date()))
    selected=frame[frame.date.isin(dates)]
    prices_wide=selected.pivot(index='date',columns='symbol',values='close')
    prices_wide['CASH']=1.
    evaluated=module.BacktestEngine(config).run_backtest(result.strategy_name,prices_wide,result.weights)
    return evaluated
