"""Prospective frozen-policy evaluation; training data cannot qualify a model."""
from datetime import datetime, timezone
import time
import pandas as pd
import torch
from .moe_live import LiveInputStream, live_snapshot
from .moe_paper import TradingMoEPaper
from .state_io import EvidenceJournal
from .expert_system import registry_owner


def evaluation_boundary(pair):
    if not pair or any('holdout_after' not in r for r in pair.values()):
        raise ValueError('evaluation snapshots need a new prospective holdout boundary')
    return max(utc_stamp(record['holdout_after']) for record in pair.values())


def utc_stamp(value):
    stamp=pd.Timestamp(value)
    return stamp.tz_localize('UTC') if stamp.tzinfo is None else stamp.tz_convert('UTC')


def future_rows(rows, pair):
    boundary=evaluation_boundary(pair)
    return [r for r in rows if utc_stamp(r['timestamp'])>boundary]


def validate_evaluation(pair,scores):
    boundary=evaluation_boundary(pair)
    if set(scores)!={'replay','paper'}:raise ValueError('both future evaluation phases are required')
    prior=None
    for phase in ('replay','paper'):
        left,right=scores[phase]['champion'],scores[phase]['candidate']
        if any(left.get(k)!=right.get(k) for k in ('first_as_of','last_as_of','decisions')):
            raise ValueError('paired evaluation used different market intervals')
        first=utc_stamp(left['first_as_of']);last=utc_stamp(left['last_as_of'])
        if first<=boundary or last<first or (prior is not None and first<=prior):
            raise ValueError('evaluation overlaps training/capture or another phase')
        prior=last
    return boundary.isoformat()


def collect_holdout(args,model,pair,notify):
    """Gather contemporaneous native evidence from Feed, without trading or learning.

    Accounts for scoring are created separately by the paired evaluator. The
    collector only maintains an empty input account for market-only preparation.
    """
    boundary=evaluation_boundary(pair)
    directory=args.state/'holdout'
    directory.mkdir(parents=True,exist_ok=True)
    journal=EvidenceJournal(directory,cache_rows=args.rules['evidence_cache_rows'])
    rows=future_rows(journal.cached_rows(),pair)
    through=rows[-1]['timestamp'] if rows else boundary.tz_convert(None).isoformat()
    stream=LiveInputStream(args.market,through)
    context_account=TradingMoEPaper(directory/'inputs',settings=args.rules).paper_account
    cache={};last={}
    while not (args.state/'stop.request').exists():
        minutes={pd.Timestamp(r['timestamp']).floor('min') for r in rows}
        if len(rows)>=args.rules['evaluation_min_observations'] and len(minutes)>=args.rules['validation_min_market_minutes']:
            return rows[-args.rules['evaluation_max_observations']:],str(journal.path)
        item=stream.next_frame()
        if item is None:
            notify(len(minutes));time.sleep(float(args.rules['inference_poll_seconds']));continue
        frame,stamp=item
        panel,index,snapshot,_=live_snapshot(model,args.market,frame,stamp,context_account)
        packets=[]
        for key in model.controller.market_ids:
            data=snapshot['expert_inputs'].get(key)
            if not data or (hasattr(model,'assembly_enabled') and key not in model.assembly_enabled):continue
            age=(pd.Timestamp(stamp)-last[key]).total_seconds() if key in last else float('inf')
            if key not in cache or age>=float(args.rules['market_expert_refresh_seconds']):
                with registry_owner(model.gpu_lock,wait=True):
                    device=model.resources.native_device(key,args.device,args.rules['native_vram_reserve_mib'])
                    with model.resources.measure('expert:'+key,device),torch.no_grad():
                        packet=model.experts[key](model.root,data,device)
                packet.update(expert=key,native_features_verified=bool(data.get('native_features_verified')))
                cache[key]=packet;last[key]=pd.Timestamp(stamp)
            packets.append(cache[key])
        if not packets:
            notify(len(minutes));continue
        row=dict(timestamp=str(panel.dates[index]),decision=dict(raw_outputs=packets,
            source_kind='live',market_path=str(args.market),as_of=str(stamp),
            trading_output={},tradable_symbols=snapshot['tradable_symbols']))
        previous=rows[-1] if rows and pd.Timestamp(rows[-1]['timestamp']).floor('min')==pd.Timestamp(row['timestamp']).floor('min') else None
        journal.record_cycle(row,replace_stamp=previous['timestamp'] if previous else None)
        if previous:rows[-1]=row
        else:rows.append(row)
        rows=rows[-args.rules['evaluation_max_observations']:]
        notify(len({pd.Timestamp(r['timestamp']).floor('min') for r in rows}))
    raise InterruptedError('future evaluation stopped; snapshots and observations are retained')
