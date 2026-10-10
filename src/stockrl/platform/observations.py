"""Point-in-time Expert inputs and compact, source-specific evidence tokens."""
import numpy as np
import pandas as pd


class InputUnavailable(ValueError):
    """The Expert's declared input contract cannot be satisfied by current data."""


def native_input(key, frame, daily, as_of, max_batch=8):
    source = frame
    intervals=frame.sort_values('date').groupby('symbol').date.diff().dt.total_seconds().dropna()
    units, seconds = "price", int(intervals[intervals>0].median()) if (intervals>0).any() else 86400
    if key in ("timesfm", "chronos"):
        if daily.empty or "SPY" not in set(daily.symbol):
            raise InputUnavailable("실제 SPY 일봉이 있어야 일별 초과수익률을 계산할 수 있습니다.")
        ordered=daily.sort_values(["symbol","date"]).drop_duplicates(["symbol","date"],keep="last").copy()
        ordered["return"]=ordered.groupby("symbol").close.pct_change(fill_method=None)
        benchmark=ordered.loc[ordered.symbol=='SPY',["date","return"]].dropna().rename(columns={"return":"benchmark"})
        source=pd.merge_asof(ordered.loc[ordered.symbol!='SPY'].sort_values('date'),benchmark.sort_values('date'),
                             on='date',direction='backward',tolerance=pd.Timedelta(days=7))
        source["close"]=source['return']-source['benchmark']
        source=source.dropna(subset=['close'])
        units, seconds = "daily_excess_return", 86400
    inputs = []
    candidates = [s for s,g in source.groupby("symbol") if len(g) >= 32 and (s != "SPY" or key not in ("chronos", "timesfm"))]
    for offset in range(0, len(candidates), max_batch):
        symbols = candidates[offset:offset+max_batch]
        rows = source[source.symbol.isin(symbols)].sort_values(["date", "symbol"])
        if key == "kronos":
            groups = [rows[rows.symbol==s].tail(128).copy() for s in symbols]
            for group in groups:
                group["timestamp"] = group.date.astype(str)
                group["amount"] = group.close*group.volume
            data = dict(symbols=symbols, bars=[g.to_dict("records") for g in groups],
                        future_timestamps=[str(pd.Timestamp(as_of)+pd.Timedelta(seconds=seconds))], amount_observed=False)
        else:
            histories=[rows[rows.symbol==s].dropna(subset=['close']).tail(128) for s in symbols]
            length=min(len(h) for h in histories)
            if key=='toto':
                length=(length//32)*32
            if length<32:continue
            histories=[h.tail(length) for h in histories]
            data = dict(symbols=symbols,series=[h.close.to_numpy(np.float32).tolist() for h in histories],
                        observation_timestamps=[h.date.astype(str).tolist() for h in histories])
        data.update(as_of=str(rows.date.max()), horizon=1, sampling_seconds=seconds,
                    frequency_id=1 if seconds>=86400 else 0, units=units, native_features_verified=True,
                    input_authenticity="point_in_time_market_feed")
        inputs.append(data)
    if not inputs:
        raise InputUnavailable("종목별 실제 관측이 32개 이상 필요합니다.")
    return inputs
