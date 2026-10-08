"""One shared frozen Expert process; market execution and training never wait on it."""
import argparse
import time
import numpy as np
import pandas as pd
import torch
from ..market_reader import IncrementalMarketCSV
from ..state_io import atomic_json
from .config import load_settings, CONFIG_PATH
from .assets import ExpertPool
from .journal import Journal
from .observations import native_input, daily_history
from .worker_state import publish, stopped


def run(settings):
    torch.set_num_threads(settings.learning.cpu_threads)
    journal = Journal(settings.state_dir/"operations.sqlite3",settings.resources.journal_limit_mib,settings.resources.retained_transitions)
    publish(settings,"experts",status="loading",message="Expert 자산 목록을 읽는 중")
    pool = ExpertPool(settings)
    atomic_json({"model_spec":pool.model_spec(),"experts":pool.catalog()},settings.state_dir/"expert_catalog.json")
    reader=IncrementalMarketCSV(settings.state_dir/"live"/"market.csv",retain_timestamps=256)
    last_run={}; cursor=0; previous_signature=None; cached_frame=None; daily_signature=None; cached_daily=pd.DataFrame()
    try:
        while not stopped(settings,"experts"):
            if not reader.path.exists():
                publish(settings,"experts",status="waiting",experts=pool.catalog(),message="실시간 시세 대기")
                time.sleep(1); continue
            frame,signature=reader.refresh()
            if frame is None or frame.empty:
                time.sleep(1); continue
            if signature!=previous_signature:
                cached_frame=frame.copy(); cached_frame['date']=pd.to_datetime(cached_frame.date,utc=True).dt.tz_localize(None)
                previous_signature=signature
            frame=cached_frame
            stamp=str(frame.date.max()); reader.processed_through=stamp
            keys=[key for key in pool.ids if not settings.enabled_experts or key in settings.enabled_experts]
            if not keys:
                time.sleep(1); continue
            key=keys[cursor%len(keys)]; cursor+=1
            policy=bool(pool.entries[key].get("stock_policy"))
            refresh=60 if policy else settings.resources.market_refresh_seconds
            if time.monotonic()-last_run.get(key,-refresh) < refresh:
                time.sleep(0.25); continue
            last_run[key]=time.monotonic()
            daily_path=reader.path.with_name('timeframes.sqlite3')
            wal_path=daily_path.with_name(daily_path.name+'-wal')
            signature=(pd.Timestamp(stamp).date(),*(p.stat().st_mtime_ns if p.exists() else 0 for p in (daily_path,wal_path)))
            if signature!=daily_signature:
                cached_daily=daily_history(daily_path,stamp);daily_signature=signature
            daily=cached_daily
            if policy:
                required=set(pool.entries[key]['stock_policy']['universe'])
                daily=daily[daily.symbol.isin(required)] if not daily.empty else daily
            account=journal.get_state("account") or {}
            book=account.get("books",{}).get("USD",{})
            nav=book.get("cash",0)+sum(p["quantity"]*book.get("marks",{}).get(s,p["average_cost"])
                                         for s,p in book.get("positions",{}).items())
            nav_history=[r['equity'] for r in journal.history('USD',128)]
            drawdown=1-nav/max([nav,*nav_history],default=1) if nav else 0
            volatility=float(np.std(np.diff(np.log(np.maximum(nav_history,1e-9))))) if len(nav_history)>1 else 0
            snapshot={"symbols":sorted(frame.symbol.unique()),"as_of":stamp,
                "stock_policy_history":[],
                "policy_account":{"cash":book.get("cash",0),"nav":nav,
                    "positions":{s:p["quantity"] for s,p in book.get("positions",{}).items()},
                    "trades":book.get("trade_count",0),"costs":sum(book.get(k,0) for k in ("fees","slippage","spread","sell_tax"))}}
            snapshot['policy_account'].update(drawdown=drawdown,volatility=volatility)
            if not daily.empty:
                snapshot["stock_policy_history"]=daily.assign(date=daily.date.astype(str)).to_dict("records")
            publish(settings,"experts",status="inference",active_expert=key,active_since=time.time(),experts=pool.catalog())
            try:
                batches=[None] if policy else native_input(key,frame,daily,stamp)
                packets=[]
                for batch_index,data in enumerate(batches):
                    if stopped(settings,'experts'):break
                    publish(settings,'experts',status='inference',active_expert=key,active_since=time.time(),batch=batch_index+1,batches=len(batches))
                    packets.append(pool.run(key,data,snapshot))
                journal.put_evidence(key,packets)
            except MemoryError as exc:
                detail=str(exc)
                if pool.metrics.get(key,{}).get("error")!=detail:
                    journal.event("warning",f"{pool.entries[key].get('name',key)}: {detail}")
                pool.metrics.setdefault(key,{}).update(status="waiting_resources",error=detail)
            except ValueError as exc:
                pool.metrics.setdefault(key,{}).update(status="needs_input",error=str(exc))
            except Exception as exc:
                detail=f"{type(exc).__name__}: {exc}"
                if pool.metrics.get(key,{}).get("error")!=detail:
                    journal.event("error",f"{pool.entries[key].get('name',key)}: {detail}")
                pool.metrics.setdefault(key,{}).update(status="error",error=detail)
            publish(settings,"experts",status="ready",active_expert=None,experts=pool.catalog(),last_as_of=stamp)
    finally:
        pool.close(); journal.close(); publish(settings,"experts",status="stopped")


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--config",default=str(CONFIG_PATH)); args=parser.parse_args()
    settings=load_settings(args.config)
    try:
        run(settings)
    except Exception as exc:
        publish(settings,"experts",status="error",error=f"{type(exc).__name__}: {exc}")
        raise
