"""Point-in-time Expert inputs and compact, source-specific evidence tokens."""
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd


def daily_history(path: Path, as_of):
    if not path.is_file():
        return pd.DataFrame()
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
        # A provider's current daily candle is incomplete. Use only prior completed UTC days.
        frame = pd.read_sql_query("SELECT symbol,stamp_ns,open,high,low,close,volume FROM daily_bars WHERE stamp_ns<?",
                                 db, params=[int(pd.Timestamp(as_of).normalize().value)])
    frame["date"] = pd.to_datetime(frame.pop("stamp_ns"))
    return frame


def native_input(key, frame, daily, as_of, max_batch=8):
    source = frame
    units, seconds = "price", 60
    if key in ("timesfm", "chronos"):
        if daily.empty or "SPY" not in set(daily.symbol):
            raise ValueError("실제 SPY 일봉이 있어야 일별 초과수익률을 계산할 수 있습니다.")
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
                        future_timestamps=[str(pd.Timestamp(as_of)+pd.Timedelta(minutes=1))], amount_observed=False)
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
                    frequency_id=1 if seconds==86400 else 0, units=units, native_features_verified=True,
                    input_authenticity="point_in_time_market_feed")
        inputs.append(data)
    if not inputs:
        raise ValueError("종목별 실제 관측이 32개 이상 필요합니다.")
    return inputs


def prepare_evidence(packets, symbols, spec, as_of, ttl=300):
    expert_ids=spec["expert_ids"]
    config=spec["config"]
    tokens={key:np.zeros((len(symbols),size),np.float32) for key,size in config["feature_sizes"].items()}
    mask=np.zeros((len(symbols),len(expert_ids)),bool)
    stock_ids=config.get("stock_policy_ids",[])
    policy_q={key:np.zeros((len(symbols),4),np.float32) for key in stock_ids}
    for key, batches in packets.items():
        if key not in expert_ids:
            continue
        e = expert_ids.index(key)
        for packet in batches if isinstance(batches, list) else [batches]:
            stamp = pd.Timestamp(packet["as_of"])
            age = (pd.Timestamp(as_of)-stamp).total_seconds()
            permitted_age = 4*86400 if packet.get("sampling_seconds")==86400 else ttl
            if age < 0 or age > permitted_age:
                continue
            native = np.asarray(packet["native_output"], np.float32)
            if packet["layout"] == "nine_quantiles,batch,variate,horizon":
                native = native[:,0].transpose(1,0,2)
            native = native.reshape(len(packet["symbols"]), -1)
            for row,symbol in enumerate(packet["symbols"]):
                if symbol not in symbols:
                    continue
                symbol_age=(pd.Timestamp(as_of)-pd.Timestamp(packet.get('symbol_as_of',{}).get(symbol,packet['as_of']))).total_seconds()
                if symbol_age<0 or symbol_age>permitted_age:continue
                n = symbols.index(symbol)
                values = native[row]
                if not np.isfinite(values).all():
                    continue
                scale=max(float(np.sqrt(np.mean(values.astype(float)**2))),1e-6)
                # Verbatim Champion adapter input: native outputs plus the three native scale/time fields.
                vector=np.r_[values/scale,np.log1p(scale),np.log1p(packet.get("horizon",1)),np.log1p(packet.get("sampling_seconds") or 0)]
                if len(vector)!=tokens[key].shape[-1]:
                    raise ValueError(f"{key}: Champion의 원본 입력 크기와 출력이 다릅니다.")
                tokens[key][n]=vector
                if key in stock_ids:
                    item=packet["common_output"][row]
                    policy_q[key][n]=[float(item[k]) for k in ("sell_score","hold_score","buy_score","target_weight")]
                mask[n,e] = True
    return tokens,mask,policy_q
