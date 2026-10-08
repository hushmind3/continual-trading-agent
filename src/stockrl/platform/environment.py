"""Shared live/replay execution semantics and settled, cost-adjusted portfolio reward."""
from __future__ import annotations

import json
from types import SimpleNamespace
import numpy as np
import pandas as pd
import torch

from ..paper_account import PaperAccount, _currency
from .observations import prepare_evidence
from .policy import observation, INPUT_KEYS


def market_view(frame):
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame.date, utc=True).dt.tz_localize(None)
    frame = frame.sort_values(["date", "symbol"]).drop_duplicates(["date", "symbol"], keep="last")
    raw = frame.pivot(index="date", columns="symbol", values="close").sort_index()
    observed = raw.notna().to_numpy()
    closes = raw.ffill().to_numpy(float)
    symbols = raw.columns.tolist()
    latest = frame.groupby("symbol").tail(1).set_index("symbol")
    groups = {s:(str(latest.loc[s,"market"]),str(latest.loc[s,"asset_class"])) for s in symbols}
    features = np.zeros((*closes.shape, 8), np.float32)
    if "spread_bps" in frame:
        features[:,:,7] = frame.pivot(index="date",columns="symbol",values="spread_bps").reindex_like(raw).fillna(0)
    return SimpleNamespace(symbols=symbols, dates=raw.index.to_numpy(dtype="datetime64[ns]"), closes=closes,
                           observed=observed, ever_observed=observed.any(0), groups=groups, features=features), frame


class PortfolioEnvironment:
    def __init__(self, settings, journal, model_spec):
        self.settings,self.journal,self.model_spec=settings,journal,model_spec
        self.account = PaperAccount.in_memory(settings.risk.fee, settings.risk.slippage)
        saved = journal.get_state("account")
        if saved:
            self.account.state = saved
        self.pending = journal.pending()
        self.peak=journal.get_state('risk_peaks') or {c:b["equity"] for c,b in self.account.snapshot()["books"].items()}

    def advance(self, view, index, enabled):
        fills = self.account.process_bar(view,index,enabled)
        return fills

    def observe(self, view, frame, index, currency, packets):
        indices = [i for i,s in enumerate(view.symbols)
                   if _currency(*view.groups[s])==currency and np.isfinite(view.closes[index,i])]
        if not indices:
            return None
        if not view.observed[index,indices].any():
            # A reference index/FX tick cannot create a new USD/KRW portfolio transition.
            return None
        symbols = [view.symbols[i] for i in indices]
        as_of = str(view.dates[index])
        pstate, astate = self.account.model_inputs(view,index)
        if self.settings.enabled_experts:
            packets={k:v for k,v in packets.items() if k in self.settings.enabled_experts}
        evidence,mask,policy_q=prepare_evidence(packets,symbols,self.model_spec,as_of,
                                              self.settings.resources.market_refresh_seconds)
        market=np.zeros((len(symbols),8),np.float32)
        context=np.column_stack([np.asarray(pstate)[indices],np.broadcast_to(astate,(len(indices),len(astate)))]).astype(np.float32)
        for n,s in enumerate(symbols):
            data = frame[(frame.symbol==s)&(frame.date<=pd.Timestamp(as_of))].tail(32)
            closes = data.close.to_numpy(float)
            returns = np.diff(np.log(np.maximum(closes,1e-9)))
            volume = data.volume.to_numpy(float)
            changes = [float(closes[-1]/closes[-1-k]-1) if len(closes)>k else 0 for k in (1,5,20)]
            age = (pd.Timestamp(as_of)-data.date.max()).total_seconds()
            market[n] = changes+[float(returns.std()) if len(returns) else 0,
                float(data.high.iloc[-1]/max(data.low.iloc[-1],1e-9)-1), float(np.log1p(volume[-1]))/20,
                min(age/self.settings.risk.freshness_seconds,10), float(view.observed[index,indices[n]])]
        current = np.asarray([pstate[i][1] for i in indices])
        fresh = np.asarray([view.observed[index,i] and np.isfinite(view.closes[index,i]) for i in indices])
        fresh = fresh & mask.any(1)
        obs=observation(evidence,mask,np.nan_to_num(context),np.nan_to_num(market),policy_q)
        book = self.account.snapshot()["books"][currency]
        self.peak[currency] = max(self.peak[currency],book["equity"])
        drawdown=1-book['equity']/max(self.peak[currency],1e-9)
        obs['market'][:,7]=float(drawdown)
        return {"observation":obs,"symbols":symbols,"current_weights":current,"fresh":fresh,
                "currency":currency,"drawdown":drawdown,
                "as_of":as_of,"coverage":int(mask.any(1).sum()),"indices":indices,"equity":book["equity"]}

    def settle(self, data, version):
        currency = data["currency"]
        pending = self.pending.get(currency)
        if not pending or pending["as_of"] >= data["as_of"]:
            return
        elapsed=(pd.Timestamp(data['as_of'])-pd.Timestamp(pending['as_of'])).total_seconds()
        outstanding={order.get('decision_id') for order in self.account.state['pending'].values()}
        unfilled=outstanding.intersection(pending.get('order_ids',[]))
        if unfilled and elapsed<self.settings.risk.freshness_seconds:
            return
        if unfilled:
            self.account.state['pending']={s:o for s,o in self.account.state['pending'].items() if o.get('decision_id') not in unfilled}
            self.journal.event('warning',f"{currency}: 관측 지연으로 미체결 주문 {len(unfilled)}개를 취소했습니다.")
        terminal = pending["symbols"] != data["symbols"] or elapsed>self.settings.risk.freshness_seconds
        reward = float(np.log(max(data["equity"],1e-9)/max(pending["equity"],1e-9)))
        td = pending["transition"]
        td["next"] = {k:td[k] if terminal else data["observation"][k] for k in INPUT_KEYS}
        td["next"]["reward"] = torch.tensor([reward*100],dtype=torch.float32)
        td["next"]["done"] = torch.tensor([terminal])
        td['next']['discount']=torch.tensor([self.settings.learning.discount**(elapsed/60)],dtype=torch.float32)
        self.journal.settle(currency,json.dumps(pending["symbols"]),pending["version"],td)
        self.pending.pop(currency,None)

    def submit(self, result, data, view, index, version, enabled):
        if not enabled or not data["coverage"] or data['currency'] in self.pending:
            return []
        weights = result.weights.weight.to_numpy(float)
        current = data["current_weights"]
        actions = np.where(weights-current>1e-5,2,np.where(weights-current < -1e-5,0,1))
        indices = data["indices"]
        sub = SimpleNamespace(dates=view.dates,symbols=data["symbols"],groups=view.groups,
                              observed=view.observed[:,indices],closes=view.closes[:,indices],features=view.features[:,indices])
        orders = self.account.queue_decisions(sub,index,np.eye(3)[actions],True,
                         np.r_[weights, result.metadata["risk"]["cash_weight"]],actions)
        transition = result.metadata["transition"].select(*INPUT_KEYS,"action","action_log_prob","state_value").to_dict()
        pending = dict(as_of=data["as_of"],symbols=data["symbols"],version=version,equity=data["equity"],transition=transition,order_ids=sorted(orders))
        self.pending[data["currency"]] = pending
        self.journal.replace_pending(data["currency"],pending)
        self.account.save()
        return sorted(orders)
