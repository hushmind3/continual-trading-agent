"""Currency and UI adapter for official FinRL-X execution and FinRL StockTradingEnv.

The model's cash-inclusive allocation head determines order budgets. Fills are
next-bar paper fills and rewards include every configured trading cost.
"""
from __future__ import annotations

import json
import math
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .state_io import atomic_json


SEED_CASH = {"KRW": 10_000_000.0, "USD": 10_000.0}
KR_SELL_TAX_ASSUMPTION = 0.001  # configurable simulation assumption, not a tax quote


def _currency(market: str, asset: str) -> str | None:
    # Explicit cash-only USDT crypto simulation in the USD seed ledger.
    # No margin/futures or implicit conversion of arbitrary crypto quotes.
    if asset == "crypto" and market == "BINANCE_USDT":
        return "USD"
    if asset not in ("equity", "etf"):
        return None
    if market in ("KRX", "KOSDAQ"):
        return "KRW"
    if market in ("US", "NYSE", "NASDAQ", "NYSEARCA", "AMEX"):
        return "USD"
    return None


class PaperAccount:
    def __init__(self, path: Path, fee: float, slippage: float):
        self.path = Path(path)
        self.fee = float(fee)
        self.slippage = float(slippage)
        self.state = self._empty_state()
        if self.path.exists():
            saved = json.loads(self.path.read_text(encoding="utf-8"))
            if saved.get("version") != 1 or set(saved.get("books", {})) != set(SEED_CASH):
                raise ValueError("paper account state schema does not match the live ledger")
            self.state = saved
            self.state.setdefault("episode_id",uuid.uuid4().hex)

    @staticmethod
    def _empty_state() -> dict:
        return {
            "version": 1,
            "episode_id": uuid.uuid4().hex,
            "last_timestamp": None,
            "pending": {},
            "fills": [],
            "books": {currency: {
                "initial_cash": seed, "cash": seed, "positions": {}, "marks": {},
                "fees": 0.0, "slippage": 0.0, "spread": 0.0,
                "sell_tax": 0.0, "realized_pnl": 0.0, "symbol_realized_pnl": {}, "trade_count": 0,
            } for currency, seed in SEED_CASH.items()},
        }

    @classmethod
    def in_memory(cls, fee: float, slippage: float):
        account=cls.__new__(cls)
        account.path=None
        account.fee=float(fee)
        account.slippage=float(slippage)
        account.state=cls._empty_state()
        return account

    def reset(self) -> None:
        """Reset a dedicated simulation ledger to the shared starting cash."""
        self.state=self._empty_state()
        self.save()

    def _equity(self, currency: str) -> float:
        book = self.state["books"][currency]
        return float(book["cash"] + sum(
            float(position["quantity"]) * float(book["marks"].get(symbol, position["average_cost"]))
            for symbol, position in book["positions"].items()))

    def symbol_net_pnl(self, symbol: str) -> float:
        """Realized plus open-position PnL for one symbol, normalized by seed cash."""
        for book in self.state["books"].values():
            if (symbol not in book["positions"] and
                    symbol not in book.get("symbol_realized_pnl", {})):
                continue
            realized = float(book.get("symbol_realized_pnl", {}).get(symbol, 0.0))
            position = book["positions"].get(symbol)
            unrealized = 0.0
            if position:
                mark = float(book["marks"].get(symbol, position["average_cost"]))
                unrealized = int(position["quantity"]) * (mark - float(position["average_cost"]))
            return (realized + unrealized) / max(float(book["initial_cash"]), 1e-9)
        return 0.0

    def model_inputs(self, panel, index: int):
        """Return per-symbol [N,8] and account [8] state for the portfolio heads."""
        n = len(panel.symbols)
        pstate = [[0.0] * 8 for _ in range(n)]
        for j, symbol in enumerate(panel.symbols):
            seen=(panel.ever_observed[j] if hasattr(panel,"ever_observed")
                  else panel.observed[:index + 1,j].any())
            if not panel.observed[index, j] and not seen:
                continue
            market, asset = panel.groups[symbol]
            currency = _currency(market, asset)
            if currency is None:
                continue
            book = self.state["books"][currency]
            price = float(panel.closes[index, j])
            if not math.isfinite(price) or price <= 0:
                price = float(book["marks"].get(symbol, 0.0))
            if price <= 0:
                continue
            book["marks"][symbol] = price
            pos = book["positions"].get(symbol)
            qty = float(pos["quantity"]) if pos else 0.0
            avg = float(pos["average_cost"]) if pos else 0.0
            value = qty * price; unreal = value - qty * avg
            equity = max(self._equity(currency), 1e-9)
            pstate[j] = [1.0 if qty else 0.0, value / equity,
                         float(book["cash"]) / equity, unreal / max(equity, 1.0),
                         qty / max(1.0, float(book["initial_cash"]) / price),
                         float(book["trade_count"]) / 1000.0,
                         float(book["fees"]) / max(equity, 1.0),
                         float(book["sell_tax"]) / max(equity, 1.0)]
        return pstate, None

    def _fill(self, symbol: str, currency: str, action: str, price: float,
              spread_rate: float, budget: float, timestamp: str,
              requested_quantity: int | None = None,
              decision_id: str | None = None,
              order_date: str | None = None) -> dict | None:
        book = self.state["books"][currency]
        half_spread = max(0.0, min(float(spread_rate) / 2.0, 0.025))
        execution_cost = half_spread + self.slippage
        position = book['positions'].get(symbol)
        old_quantity=int(position['quantity']) if position else 0
        old_average=float(position['average_cost']) if position else 0.
        requested=(max(0,int(requested_quantity)) if requested_quantity is not None else
            math.floor(budget/(price*(1+execution_cost)*(1+self.fee))) if action=='BUY' else
            min(old_quantity,int(budget) if budget>0 else old_quantity))
        if action not in ('BUY','SELL') or requested<1:return None
        from .platform.finrl_modules import StockTradingEnv
        import numpy as np
        import pandas as pd
        fill_price=price*(1+execution_cost if action=='BUY' else max(0,1-execution_cost))
        frame=pd.DataFrame({'date':[timestamp,timestamp],'tic':[symbol,symbol],
            'close':[fill_price,price],'tradable':[False,False]})
        tax_rate=KR_SELL_TAX_ASSUMPTION if currency=='KRW' else 0.
        env=StockTradingEnv(frame,1,requested,book['cash'],[old_quantity],
            [self.fee],[self.fee+tax_rate],1.,4,1,['tradable'],print_verbosity=10**9)
        env.step(np.array([1. if action=='BUY' else -1.]))
        new_quantity=int(env.state[2]);quantity=abs(new_quantity-old_quantity)
        if not quantity:return None
        book['cash']=float(env.state[0])
        notional=quantity*fill_price;fee=notional*self.fee
        tax=notional*tax_rate if action=='SELL' else 0.
        realized=notional-fee-tax-quantity*old_average if action=='SELL' else 0.
        if action=='BUY':
            book['positions'][symbol]={'quantity':new_quantity,'average_cost':(old_quantity*old_average+notional+fee)/new_quantity,
                'opened_timestamp':position.get('opened_timestamp',timestamp) if position else timestamp}
        else:
            book['realized_pnl']+=realized
            symbol_realized=book.setdefault('symbol_realized_pnl',{})
            symbol_realized[symbol]=symbol_realized.get(symbol,0.)+realized
            if new_quantity:position['quantity']=new_quantity
            else:book['positions'].pop(symbol,None)
        book["trade_count"] += 1
        book["fees"] += fee
        book["sell_tax"] += tax
        book["spread"] += quantity * price * half_spread
        book["slippage"] += quantity * price * self.slippage
        statistics=book.setdefault("trade_statistics",{
            "first_timestamp":timestamp,"buy_count":0,"sell_count":0,
            "sell_wins":0,"sell_losses":0,"sell_flat":0,"sell_realized_sum":0.0,
            "holding_count":0,"holding_seconds_sum":0.0,
            "holding_seconds_min":None,"holding_seconds_max":None})
        statistics["last_timestamp"]=timestamp
        statistics["buy_count" if action=="BUY" else "sell_count"]+=1
        holding_seconds=None
        if action=="SELL":
            statistics["sell_wins" if realized>0 else "sell_losses" if realized<0 else "sell_flat"]+=1
            statistics["sell_realized_sum"]+=realized
            if position.get("opened_timestamp"):
                def utc(value):
                    parsed=datetime.fromisoformat(str(value)[:26].replace("Z","+00:00"))
                    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
                try:
                    holding_seconds=max(0,(utc(timestamp)-utc(position["opened_timestamp"])).total_seconds())
                except (ValueError,TypeError):
                    holding_seconds=None
                if holding_seconds is not None:
                    statistics["holding_count"]+=1
                    statistics["holding_seconds_sum"]+=holding_seconds
                    for key,fn in (("holding_seconds_min",min),("holding_seconds_max",max)):
                        statistics[key]=holding_seconds if statistics[key] is None else fn(statistics[key],holding_seconds)
        fill={"date": timestamp, "symbol": symbol,
            "sequence":book['trade_count'],
            "currency": currency, "action": action, "quantity": quantity,
            "price": fill_price, "fee": fee, "sell_tax": tax,
            "realized_pnl": realized, "decision_id": decision_id,
            "order_date": order_date,"holding_seconds":holding_seconds}
        self.state["fills"].append(fill)
        self.state["fills"] = self.state["fills"][-200:]
        if book["cash"] < -1e-6 or any(p["quantity"] < 0 for p in book["positions"].values()):
            raise AssertionError("paper account spent more cash or sold more shares than it owns")
        return fill

    def process_bar(self, panel, index: int, enabled: bool) -> list[dict]:
        timestamp = str(panel.dates[index])
        if self.state["last_timestamp"] and timestamp <= self.state["last_timestamp"]:
            return []
        if not enabled:
            self.state["pending"].clear()
        filled=[]
        for j, symbol in enumerate(panel.symbols):
            if not panel.observed[index, j]:
                continue
            market, asset = panel.groups[symbol]
            currency = _currency(market, asset)
            if currency is None:
                continue
            price = float(panel.closes[index, j])
            if not math.isfinite(price) or price <= 0:
                continue
            book = self.state["books"][currency]
            book["marks"][symbol] = price
            order = self.state["pending"].get(symbol)
            if enabled and order and order["date"] < timestamp:
                # The completed bar close is known only now. The prior signal
                # could not trade on its own observation bar.
                spread_bps = max(0.0, float(panel.features[index, j, 7]))
                symbol_pnl_before_fill=self.symbol_net_pnl(symbol)
                fill=self._fill(symbol, currency, order["action"], price,
                           spread_bps / 10_000.0, float(order.get("budget", 0.0)), timestamp,
                           requested_quantity=(int(order["requested_quantity"])
                                               if order.get("requested_quantity") is not None else None),
                           decision_id=order.get("decision_id"),
                           order_date=order.get("date"))
                if fill is not None:
                    fill["symbol_pnl_before_fill"]=symbol_pnl_before_fill
                    filled.append(fill)
                del self.state["pending"][symbol]
        self.state["last_timestamp"] = timestamp
        return filled

    def queue_decisions(self,panel,index,probabilities,enabled,allocation=None,actions=None):
        if not enabled:return set()
        if allocation is None:raise ValueError('목표 비중과 현금 비중이 필요합니다.')
        import pandas as pd
        from .platform.finrl_modules import TradeExecutor,ExecutionConfig,OrderResponse
        from strategies.base_strategy import BaseStrategy,StrategyConfig,StrategyResult
        stamp=str(panel.dates[index]);account=self;queued=set()
        class BrokerAdapter:
            accounts={key:None for key in SEED_CASH}
            def set_account(self,name):self.currency=name
            def get_portfolio_value(self,name):return account._equity(name)
            def get_account_info(self,name):
                return {'cash':account.state['books'][name]['cash'],'equity':self.get_portfolio_value(name),'portfolio_value':self.get_portfolio_value(name)}
            def get_positions(self,name):
                book=account.state['books'][name]
                return [{'symbol':s,'market_value':p['quantity']*book['marks'].get(s,p['average_cost'])} for s,p in book['positions'].items()]
            def place_order(self,order,name):
                quantity=math.floor(order.quantity+1e-9)
                if quantity<1:raise ValueError('정수 수량이 1 미만입니다.')
                identity=uuid.uuid4().hex;symbol=order.symbol
                account.state['pending'][symbol]={'date':stamp,'action':order.side.upper(),'requested_quantity':quantity,
                    'budget':quantity if order.side=='sell' else quantity*book_price(symbol,name),'decision_id':identity,'currency':name}
                queued.add(identity)
                return OrderResponse(identity,'accepted',symbol,quantity,0,order.side,'market',datetime.now(timezone.utc))
        class TargetStrategy(BaseStrategy):
            def __init__(self,weights):super().__init__(StrategyConfig(name='Champion'));self.weights=weights
            def generate_weights(self,data,target_date=None):return StrategyResult('Champion',self.weights,{})
        def book_price(symbol,currency):
            price=account.state['books'][currency]['marks'].get(symbol,0)
            if not math.isfinite(price) or price<=0:raise ValueError('유효한 실제 가격이 없습니다: '+symbol)
            return price
        broker=BrokerAdapter();config=ExecutionConfig(min_order_size=0,risk_checks_enabled=False,execution_timeout=0,log_orders=False)
        executor=TradeExecutor(broker,config);executor._gvkey_to_ticker=lambda symbol:symbol
        executor._get_current_price=book_price
        for currency in SEED_CASH:
            rows=[{'gvkey':s,'weight':float(allocation[j])} for j,s in enumerate(panel.symbols)
                if _currency(*panel.groups[s])==currency and panel.observed[index,j]]
            if rows:executor.execute_strategy(TargetStrategy(pd.DataFrame(rows)),{},currency,stamp)
        self.save();return queued

    def snapshot(self) -> dict:
        books = {}
        for currency, book in self.state["books"].items():
            equity = self._equity(currency)
            books[currency] = {**book, "equity": equity,
                "net_pnl": equity - float(book["initial_cash"]),
                "holdings_value": equity - float(book["cash"])}
        return {**self.state, "books": books,
                "execution": "next completed bar close; cash-only equities and ETFs",
                "allocation": "per-currency tradable model weights; action-gated whole-share orders with cost-aware cash limits",
                "kr_sell_tax_assumption": KR_SELL_TAX_ASSUMPTION}

    def save(self) -> None:
        if self.path is not None:
            atomic_json(self.snapshot(), self.path)
