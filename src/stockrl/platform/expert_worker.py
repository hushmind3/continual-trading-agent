"""One shared frozen Expert process; market execution and training never wait on it."""
import argparse
import time
import pandas as pd
import torch
from ..market_reader import IncrementalMarketCSV
from ..state_io import atomic_json
from .config import load_settings, CONFIG_PATH
from .assets import ExpertPool,guard_model_assets
from .expert_jobs import run_job
from .journal import Journal
from .observations import daily_history
from .expert_inputs import snapshot_for
from .worker_state import publish, stopped
from .selection import selection,SlotDisabled
import gc


def run(settings,config=CONFIG_PATH):
    torch.set_num_threads(settings.learning.cpu_threads)
    weight_reads=guard_model_assets(settings.resolve(settings.expert_checkpoint))
    journal = Journal(settings.state_dir/"operations.sqlite3",settings.resources.journal_limit_mib,settings.resources.retained_transitions)
    publish(settings,"experts",status="loading",message="Expert 자산 목록을 읽는 중")
    pool = ExpertPool(settings,keep_device=settings.resources.gpu_resident,live=True)
    pool.metrics=journal.get_state('expert_metrics') or {}
    if settings.resources.gpu_resident:
        _,initial=selection(settings,pool.active)
        pool.residency.preload(sorted(initial),lambda **v:publish(settings,'experts',status='loading',message=f"Expert GPU 상주 준비 · {v['completed']+1}/{v['total']}",experts=pool.catalog()))
        journal.set_state('expert_metrics',pool.metrics)
    atomic_json({"model_spec":pool.model_spec(),"experts":pool.catalog()},settings.state_dir/"expert_catalog.json")
    reader=IncrementalMarketCSV(settings.state_dir/"live"/"market.csv",retain_timestamps=256)
    last_run={}; cursor=0; previous_signature=None; cached_frame=None; daily_signature=None; cached_daily=pd.DataFrame()
    try:
        while not stopped(settings,"experts"):
            _,active=selection(settings,pool.active)
            added=set(active)-pool.active
            pool.active=set(active)
            for inactive in set(pool.loaded)-pool.active:
                pool.release(inactive)
            if settings.resources.gpu_resident and added:pool.residency.preload(sorted(added))
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
            keys=[key for key in pool.ids if key in pool.active]
            if not keys:
                publish(settings,'experts',status='ready',active_expert=None,experts=pool.catalog(),message='사용 중인 Expert 슬롯 없음')
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
            publish(settings,"experts",status="inference",active_expert=key,active_since=time.time(),experts=pool.catalog())
            try:
                batches,snapshot=snapshot_for(pool.entries[key],frame,journal,daily_path,daily)
                if not settings.resources.gpu_resident and int(pool.entries[key].get('parameters',0))>=settings.resources.isolated_expert_parameters:
                    packets=run_job(settings,key,batches,pool.metrics,config)
                else:
                    packets=[]
                    for batch_index,data in enumerate(batches):
                        if stopped(settings,'experts'):break
                        publish(settings,'experts',status='inference',active_expert=key,active_since=time.time(),batch=batch_index+1,batches=len(batches))
                        packets.append(pool.run(key,data,snapshot))
                    pool.metrics[key]['weight_files']=sorted(weight_reads)
                journal.put_evidence(key,packets)
            except SlotDisabled:
                publish(settings,'experts',status='ready',active_expert=None,experts=pool.catalog())
                continue
            except InterruptedError:
                break
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
            journal.set_state('expert_metrics',pool.metrics)
    finally:
        pool.close(); journal.close(); publish(settings,"experts",status="stopped")


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--config",default=str(CONFIG_PATH)); args=parser.parse_args()
    settings=load_settings(args.config)
    try:
        run(settings,args.config)
    except Exception as exc:
        publish(settings,"experts",status="error",error=f"{type(exc).__name__}: {exc}")
        raise
