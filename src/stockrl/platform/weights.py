"""FinRL-X weight strategy, timing and currency-specific portfolio risk overlay."""
from __future__ import annotations

import numpy as np
import pandas as pd
from strategies.base_strategy import BaseStrategy, StrategyConfig, StrategyResult


def risk_overlay(proposed, current, fresh, settings, *, drawdown=0.0):
    proposed = np.asarray(proposed, float)
    current = np.asarray(current, float)
    fresh = np.asarray(fresh, bool)
    if not np.isfinite(proposed).all() or not np.isfinite(current).all():
        raise ValueError("비중에 유효하지 않은 수치가 있습니다.")
    result = np.where(fresh, np.clip(proposed, 0, settings.max_asset_weight), current)
    reason = None
    if drawdown >= settings.max_drawdown:
        result[fresh] = 0
        reason = "최대 손실폭 제한"
    locked = result[~fresh].sum()
    budget = max(0., settings.max_exposure-locked)
    active_total = result[fresh].sum()
    if active_total > budget:
        result[fresh] *= budget/active_total
    delta = result-current
    turnover = np.abs(delta).sum()
    if turnover > settings.max_turnover and drawdown < settings.max_drawdown:
        result = current + delta*(settings.max_turnover/turnover)
    if (result < -1e-9).any() or result.sum() > 1+1e-6:
        raise ValueError("통화별 현금 포함 비중이 완전하지 않습니다.")
    return result, {"turnover": float(np.abs(result-current).sum()), "cash_weight": float(1-result.sum()),
                    "frozen_assets": int((~fresh).sum()), "blocked_reason": reason}


class PortfolioStrategy(BaseStrategy):
    def __init__(self, actor, critic, risk):
        super().__init__(StrategyConfig(name="Frozen Expert / PPO allocation"))
        self.actor, self.critic, self.risk = actor, critic, risk

    def generate_weights(self, data, target_date=None):
        from .policy import decide
        weights, transition = decide(self.actor, self.critic, data["observation"], explore=data.get("explore",False))
        target, risk = risk_overlay(weights[:-1], data["current_weights"], data["fresh"], self.risk,
                                   drawdown=data.get("drawdown",0))
        frame = pd.DataFrame({"gvkey": data["symbols"], "weight": target})
        return StrategyResult(self.config.name, frame, {"as_of": target_date, "risk": risk,
                                                       "transition": transition, "currency": data["currency"]})


def evaluate_recorded_weights(prices: pd.DataFrame, weights: pd.DataFrame, fee: float, initial_capital=10000):
    """bt uses the same target-weight contract and next-observation timing."""
    import bt
    if prices.empty or weights.empty:
        raise ValueError("평가할 실제 가격과 비중 기록이 필요합니다.")
    signals = weights.reindex(weights.index.union(prices.index)).sort_index().ffill()
    signals = signals.reindex(prices.index).shift(1).fillna(0)
    strategy = bt.Strategy("FinRL-X", [bt.algos.WeighTarget(signals), bt.algos.Rebalance()])
    test = bt.Backtest(strategy, prices, initial_capital=initial_capital,
                       commissions=lambda quantity, price: abs(quantity*price)*fee, integer_positions=False)
    result = bt.run(test)
    values=result.prices.iloc[:,0]
    return {'first':str(values.index[0]),'last':str(values.index[-1]),'observations':len(values),
            'return_rate':float(values.iloc[-1]/values.iloc[0]-1),
            'max_drawdown':float((values/values.cummax()-1).min()),
            'final_nav':float(initial_capital*values.iloc[-1]/values.iloc[0]),
            'engine':'bt / recorded target weights'}
