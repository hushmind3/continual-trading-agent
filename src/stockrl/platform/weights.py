"""FinRL-X model-selected weights, cash accounting and recorded-weight evaluation."""
from __future__ import annotations

import numpy as np
import pandas as pd
from strategies.base_strategy import BaseStrategy, StrategyConfig, StrategyResult


def executable_weights(proposed, current, fresh):
    proposed = np.asarray(proposed, float)
    current = np.asarray(current, float)
    fresh = np.asarray(fresh, bool)
    if not np.isfinite(proposed).all() or not np.isfinite(current).all():
        raise ValueError("비중에 유효하지 않은 수치가 있습니다.")
    if (proposed<0).any() or (proposed>1).any():
        raise ValueError("현금 계좌의 목표 비중은 0과 1 사이여야 합니다.")
    result = np.where(fresh, proposed, current)
    locked = result[~fresh].sum()
    budget = max(0., 1-locked)
    active_total = result[fresh].sum()
    if active_total > budget:
        result[fresh] *= budget/active_total
    if (result < -1e-9).any() or result.sum() > 1+1e-6:
        raise ValueError("통화별 현금 포함 비중이 완전하지 않습니다.")
    return result, {"turnover": float(np.abs(result-current).sum()), "cash_weight": float(1-result.sum()),
                    "frozen_assets": int((~fresh).sum())}


class PortfolioStrategy(BaseStrategy):
    def __init__(self, actor, critic):
        super().__init__(StrategyConfig(name="Frozen Expert / SAC allocation"))
        self.actor, self.critic = actor, critic

    def generate_weights(self, data, target_date=None):
        from .policy import decide
        weights, transition = decide(self.actor, self.critic, data["observation"], explore=data.get("explore",False))
        target, risk = executable_weights(weights[:-1], data["current_weights"], data["fresh"])
        frame = pd.DataFrame({"gvkey": data["symbols"], "weight": target})
        return StrategyResult(self.config.name, frame, {"as_of": target_date, "risk": risk,
                                                       "transition": transition, "currency": data["currency"]})


def evaluate_recorded_weights(prices: pd.DataFrame, weights: pd.DataFrame, fee: float, initial_capital=10000):
    """Official FinRL-X engine and its native weight normalization."""
    from .finrl_modules import BacktestEngine,BacktestConfig
    if prices.empty or weights.empty:
        raise ValueError("평가할 실제 가격과 비중 기록이 필요합니다.")
    signals = weights.reindex(weights.index.union(prices.index)).sort_index().ffill()
    signals = signals.reindex(prices.index).shift(1).fillna(0)
    config=BacktestConfig(str(prices.index.min().date()),str(prices.index.max().date()),
        initial_capital=initial_capital,transaction_cost=fee,integer_positions=False,benchmark_tickers=[])
    engine=BacktestEngine(config)
    result=engine.run_backtest('FinRL-X SAC',prices,signals)
    values=result.portfolio_values
    return {'first':str(values.index[0]),'last':str(values.index[-1]),'observations':len(values),
            'return_rate':float(values.iloc[-1]/values.iloc[0]-1),
            'max_drawdown':float(result.metrics.get('max_drawdown',0.)),
            'final_nav':float(initial_capital*values.iloc[-1]/values.iloc[0]),
            'engine':'FinRL-X BacktestEngine','metrics':result.metrics}
