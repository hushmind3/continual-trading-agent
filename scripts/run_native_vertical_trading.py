"""Immediate native vertical MoE paper run. No repeat downloads or 14-model probe.

Uses official ETH 36+9 observations, real daily stock excess returns and real
archival AAPL ITCH. Every evidence timestamp is recorded; archival ITCH is not
claimed to be a contemporaneous ETH order book.
"""
import argparse
from copy import deepcopy
import json
import hashlib
from pathlib import Path
import sys
import time
import os
from datetime import datetime,timezone
import numpy as np
import pandas as pd
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from stockrl.trading_moe import TradingMoE,parameter_digest
from stockrl.moe_paper import TradingMoEPaper
from stockrl.moe_training import update_batch
from stockrl.market_panel import GlobalMarketPanel
from stockrl.expert_registry import atomic_json
from stockrl.expert_system import registry_owner
from stockrl.paths import TRADING_MOE_CHECKPOINT
from stockrl.state_io import EvidenceJournal, WorkerLog
from stockrl.moe_live import LiveInputStream, live_snapshot
from stockrl.moe_promotion import save_runtime_state,trainable_path
from stockrl.operating_rules import operating_rules,RULES_PATH
from stockrl.gpu_scheduler import release_offloaded_pages

worker_status_path=None


def publish_worker(state,model=None,bridge=None,row=None,decision=None,learning=None,**changes):
    """Small polling snapshot; native evidence stays in the diagnostic registry."""
    path=state/"worker_status.json"
    try:data=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError):data={}
    data.update(changes,pid=os.getpid(),updated_at=datetime.now(timezone.utc).isoformat())
    if model is not None:
        data['resources']=model.resources.snapshot()
        data['stable_policy']=getattr(model,'stable_policy',False)
        data.update(optimizer_updates=model.optimizer_updates,
            applied_replay_rows=len(model.config.get("applied_replay_rows",{})))
        learner_device=next(model.controller.parameters()).device
        data["compute"]={"inference_device":"cuda:0" if torch.cuda.is_available() else "cpu",
            "learning_device":str(learner_device),"gpu_name":torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "allocated_bytes":torch.cuda.memory_allocated(0) if torch.cuda.is_available() else 0,
            "reserved_bytes":torch.cuda.memory_reserved(0) if torch.cuda.is_available() else 0,
            "expert_gpu_limit":1,"expert_storage":"memory-mapped PT / sequential CUDA"}
    if bridge is not None:
        data.update(books=bridge.paper_account.snapshot()["books"],fills=bridge.paper_account.state["fills"][-20:],
            pending_orders=bridge.paper_account.state["pending"],reward_points=bridge.paper_account.reward_points(),replay=bridge.replay.stats())
        if model is not None:
            applied=bridge.replay.retained_row_count(model.config.get("applied_replay_rows",{}))
            data["replay"].update(awaiting_checkpoint=applied,
                remaining_for_update=max(0,data["replay"]["untrained"]-applied))
    if row:data.update(market_timestamp=row["timestamp"],cycle_seconds=row["seconds"])
    if decision:
        output=decision["trading_output"];symbols=list(output["actions"])
        primary='ETHUSDT' if 'ETHUSDT' in symbols else next(iter(decision.get('tradable_symbols') or symbols))
        data['decisions']={s:dict(symbol=s,action=output['actions'][s],target_weight=output['target_weights'][s],
            current_weight=decision['current_weights'].get(s,0),as_of=decision['as_of']) for s in symbols}
        data['decision']={**data['decisions'][primary], 'cash_weights_by_currency':output['cash_weights_by_currency'],
            'value':decision['fusion_output']['native_head_output']['value'][0][symbols.index(primary)],
            'seconds':decision.get('native_decision_seconds',decision['decision_seconds'])}
        data['expert_status']=decision.get('expert_status',{})
        data['stages']={'market':bool(set(decision['used_experts']) & set(model.controller.market_ids)),
            'state':True,'policy':bool(set(decision['used_experts']) & set(model.controller.policy_ids)),'controller':True,'action':True}
    if getattr(model,'online_learner',None):
        data['learner']=dict(model.online_learner.stats)
        data['learning_active']=model.online_learner.busy
        data['learning_error']=model.online_learner.error
        if 'error' not in changes:data['error']=model.online_learner.error
    if learning:data["learning"]={"loss":learning["loss"],"reward_points":learning["reward_points"],"updated_at":data["updated_at"]}
    atomic_json(path,data)


def save_contexts(state,contexts,evidence=None):
    # Retain the evidence used by each pending action, including an action
    # immediately before market-cache refresh. Never relabel it as newer data.
    (evidence or EvidenceJournal(state)).save_contexts(contexts)


def training_context(snapshot,decision):
    # Native outputs already contain the learning input; do not retain a full
    # multi-year stock history again for every reward waiting to mature.
    snapshot={k:v for k,v in snapshot.items() if k not in ('expert_inputs','stock_policy_history','policy_account')}
    decision={k:v for k,v in decision.items() if k!='fusion_output'}
    return snapshot,decision


def publish_paper_status(root,state,bridge,decision,row,model,completed=False):
    registry=Path("runtime/trading_moe/registry.json")
    if not registry.is_file():return
    document=json.loads(registry.read_text(encoding="utf-8"))
    pipeline=document.setdefault("pipeline",{})
    previous=pipeline.get("paper_trading",{})
    paper={**previous,"timestamp":row["timestamp"],"books":row["books"],"fills":bridge.paper_account.state["fills"][-20:],
        "pending_orders":dict(bridge.paper_account.state["pending"]),"reward_points":bridge.paper_account.reward_points(),
        "optimizer_updates":model.optimizer_updates,"cycle_seconds":row["seconds"] if decision else previous.get("cycle_seconds"),"checkpoint":str(getattr(model,"runtime_checkpoint",TRADING_MOE_CHECKPOINT)),
        "replay":bridge.replay.stats(),"status":"paper_complete" if completed else "paper_running","live_executable":False}
    pipeline["paper_trading"]=paper
    if decision:
        paper["actions"]=decision["trading_output"]["actions"];paper["target_weights"]=decision["trading_output"]["target_weights"]
        paper["tradable_symbols"]=decision.get("tradable_symbols")
        destination=root/"inference/runs/native_vertical";destination.mkdir(parents=True,exist_ok=True)
        for packet in decision["raw_outputs"]:
            raw=json.dumps(packet).encode();target=destination/(packet["expert"]+".json");target.write_bytes(raw)
            entry=next(e for e in document["experts"] if e["id"]==packet["expert"])
            entry.update(raw_output_path=str(target),raw_output_sha256=hashlib.sha256(raw).hexdigest(),raw_output_origin="runtime_inference",
                last_used_at=pd.Timestamp.now(tz="UTC").isoformat(),last_output_shape=packet["output_shape"],last_input_shapes=packet["input_shapes"],
                router_selected=True,last_timings={"cold_load_seconds":packet.get("cold_load_seconds"),"gpu_transfer_seconds":packet.get("gpu_transfer_seconds"),
                    "forward_seconds":packet.get("forward_seconds"),"round_trip_seconds":packet.get("worker_seconds")})
        atomic_json(destination/"TradingMoE.json",decision)
        pipeline.update(stage="complete",result_path=str(destination/"TradingMoE.json"),selected_experts=decision["used_experts"],completed_experts=len(decision["used_experts"]),
            fusion_head_status="trainable_vertical_controller",as_of=decision["as_of"],timings={"total_seconds":decision["decision_seconds"]})
    atomic_json(registry,document)


def market_inputs(root,frame,index):
    stamp=pd.Timestamp(frame.iloc[index].timestamp)
    bars=frame.iloc[max(0,index-127):index+1].copy()
    price={"symbols":["ETHUSDT"],"as_of":str(stamp),"series":[bars.close.astype(float).tolist()],
        "observation_timestamps":[bars.timestamp.astype(str).tolist()],"horizon":1,"sampling_seconds":60,
        "frequency_id":0,"units":"price","input_authenticity":"real_official_ETHUSDT_price"}
    excess=pd.read_csv(root/"sources/TSFM_Finance/data/two_stocks_excess_returns.csv")
    excess=excess[pd.to_datetime(excess.TradingDate)<stamp.normalize()].tail(128)
    rates={"symbols":["AAPL"],"as_of":str(pd.Timestamp(excess.TradingDate.iloc[-1])),"horizon":1,
        "sampling_seconds":86400,"units":"daily_excess_return","series":[excess.AAPL.astype(float).tolist()],
        "observation_timestamps":[excess.TradingDate.tolist()],"input_authenticity":"real_official_daily_excess_return"}
    candles=bars[["timestamp","open","high","low","close","volume"]].copy()
    candles["timestamp"]=candles.timestamp.astype(str)
    candles["amount"]=candles.close*candles.volume
    candles_input={"symbols":["ETHUSDT"],"as_of":str(stamp),"horizon":1,"sampling_seconds":60,
        "bars":[candles.to_dict("records")],"future_timestamps":[str(stamp+pd.Timedelta(minutes=1))],
        "amount_observed":False,"input_authenticity":"real_ETHUSDT_OHLCV_amount_price_volume_proxy"}
    itch=json.loads((root/"native_data/MarketGPT/AAPL-20191230-native.json").read_text())
    return {"timesfm":rates,"chronos":rates,"toto":price,"kronos":candles_input,
        "fincast":price,"exaone":price,"timemoe":price,"marketgpt":itch}


def runtime_modes(state,rules=None):
    """Named models share the operator's flags; standalone MoE keeps its own lifecycle."""
    if state.name not in ("champion_moe", "candidate_moe"):
        return dict(observe_enabled=True, paper_enabled=True, learning_enabled=True)
    try:
        flags=json.loads((state.parent/"autonomy.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(observe_enabled=False, paper_enabled=False, learning_enabled=False)
    modes={key:bool(flags.get(key,False)) for key in ("observe_enabled","paper_enabled","learning_enabled")}
    if (rules or operating_rules())['stable_champion'] and state.name=='champion_moe':modes['learning_enabled']=False
    return modes


def commit_learning(model,bridge,contexts,records):
    ack={};credited=model.config.setdefault('applied_replay_contexts',{})
    for exp,_,_ in records:
        credited[exp.timestamp]=True
    for stamp in credited:ack.update(bridge.replay.context_row_ids(stamp))
    if records:
        ends=[str(exp.reward_end_timestamp or exp.timestamp) for exp,_,_ in records]
        model.config['training_cutoff']=max([model.config.get('training_cutoff',''),*ends])
    model.config.setdefault('applied_replay_rows',{}).update({str(k):1 for k in ack})
    pending_stamps={item['timestamp'] for item in bridge.pending}
    for stamp in credited:
        if stamp not in pending_stamps:contexts.pop(stamp,None)


def learn_saved_contexts(model,optimizer,bridge,contexts,settings=None):
    rules=settings or operating_rules()
    learner=getattr(model,'online_learner',None)
    latest=None;logs=[]
    if learner:
        completed=learner.poll(model,optimizer)
        if completed:
            latest,records=completed;commit_learning(model,bridge,contexts,records);logs.append(latest)
        if learner.busy:return latest,logs
    batch=bridge.replay.pending_batch(int(rules['training_batch_size']),
        exclude_row_ids={int(k) for k in model.config.get('applied_replay_rows',{})},timestamps=contexts,portfolio_values_only=True)
    records=[];credited=model.config.setdefault('applied_replay_contexts',{})
    for exp in batch:
        if exp.timestamp in credited:continue
        if exp.source!='paper_account_portfolio' or not exp.portfolio_value_transition:continue
        context=contexts.get(exp.timestamp)
        if context:records.append((exp,*context))
    if records:
        if learner:learner.submit(records)
        else:
            for _ in range(int(rules['training_optimizer_steps'])):
                latest=update_batch(model,optimizer,records,settings=rules)
            logs.append(latest);commit_learning(model,bridge,contexts,records)
    else:commit_learning(model,bridge,contexts,[])
    return latest,logs


def finish_learning(model,optimizer,bridge,contexts):
    learner=getattr(model,'online_learner',None)
    if learner:
        completed=learner.poll(model,optimizer,wait=True)
        if completed:commit_learning(model,bridge,contexts,completed[1])
        learner.close()



def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,required=True);p.add_argument("--steps",type=int,default=6)
    p.add_argument("--state",type=Path,default=Path("runtime/trading_moe/native_vertical"))
    p.add_argument("--checkpoint",type=Path,help="use this named model file without renaming or copying it")
    p.add_argument("--recipe",type=Path,help="shared expert base with a separate small learned state")
    p.add_argument('--mode',choices=('live','historical'),default='historical')
    p.add_argument('--market',type=Path,help='completed collector CSV for live mode')
    p.add_argument('--settings',type=Path,default=RULES_PATH,help='single operating settings file')
    p.add_argument("--device",default="cuda:0");p.add_argument("--resume",action="store_true")
    p.add_argument("--continuous",action="store_true",help="keep one model resident and run until stop.request")
    p.add_argument("--interval",type=float,help="legacy argument; cadence is configured by inference_poll_seconds")
    args=p.parse_args()
    args.state.mkdir(parents=True,exist_ok=True)
    sys.stdout=sys.stderr=WorkerLog(args.state/"activity.log")
    global worker_status_path
    worker_status_path=args.state/"worker_status.json"
    with registry_owner(args.state/"worker-owner.lock"):
        run(args)


def run(args):
    args.rules=operating_rules(getattr(args,'settings',None))
    args.interval=float(args.rules['inference_poll_seconds'])
    torch.set_num_threads(int(args.rules['cpu_threads']))
    checkpoint=args.checkpoint or TRADING_MOE_CHECKPOINT
    publish_worker(args.state,status="loading",load_count=0,error=None,stop_requested=False,gpu_waiting=False,gpu_wait_seconds=0,message=f"{checkpoint.name}를 한 번 적재하는 중입니다.")
    load_started=time.perf_counter()
    from stockrl.gpu_scheduler import ResourceMonitor
    resources=ResourceMonitor();resources.reserve_mib=int(args.rules['native_vram_reserve_mib'])
    with resources.measure('model_load'):
        model,saved=TradingMoE.load_checkpoint(checkpoint)
    model.resources=resources
    assembly_recipe=None
    if args.recipe:
        assembly_recipe=json.loads(args.recipe.read_text(encoding="utf-8"))
        if not trainable_path(checkpoint).is_file():
            model.apply_assembly_recipe(assembly_recipe)
            if assembly_recipe.get("trainable_state"):
                saved=model.load_assembly_state(assembly_recipe["trainable_state"])
                model.apply_assembly_recipe(assembly_recipe)
    model.runtime_checkpoint=checkpoint
    if args.device.startswith("cuda") and not torch.cuda.is_available():raise RuntimeError("CUDA is required for the requested GPU worker")
    model.set_learning_device(args.device)
    release_offloaded_pages()
    publish_worker(args.state,model,status="loading",load_count=1,load_seconds=time.perf_counter()-load_started,
        parameters=sum(p.numel() for p in model.parameters()),checkpoint_bytes=checkpoint.stat().st_size,message="계좌와 optimizer 상태를 복원하는 중입니다.")
    groups=model.parameter_groups()
    optimizer=torch.optim.AdamW(groups,lr=float(args.rules['learning_rate']))
    if args.resume and saved:
        optimizer.load_state_dict(saved)
        for group in optimizer.param_groups:group['lr']=float(args.rules['learning_rate'])
    if args.resume and getattr(model,'resume_rng',None):
        from torchrl.checkpoint import GlobalRNGState
        GlobalRNGState().load_state_dict(model.resume_rng)
    model.stable_policy=args.rules['stable_champion'] and args.state.name=='champion_moe'
    bridge=TradingMoEPaper(args.state,settings=args.rules,collect_experience=not model.stable_policy)
    publish_worker(args.state,model,bridge,effective_settings=args.rules)
    def gpu_wait(waiting,seconds):
        publish_worker(args.state,model,bridge,gpu_waiting=waiting,gpu_wait_seconds=seconds,
            message="다른 모델의 GPU 작업을 기다립니다 · 종료하지 않고 차례대로 실행" if waiting else "GPU 차례 확보 · 가상매매를 이어 실행합니다.")
    model.gpu_wait_callback=gpu_wait
    episode=bridge.paper_account.state["episode_id"]
    if model.config.get("replay_account_episode")!=episode:
        model.config["applied_replay_rows"]={}
        model.config['applied_replay_contexts']={}
        model.config["replay_account_episode"]=episode
    from stockrl.moe_learner import AsyncLearner
    if not model.stable_policy:model.online_learner=AsyncLearner(model,optimizer,args.rules)
    if getattr(args,'mode','historical')=='live':
        if not args.market:raise ValueError('live mode requires --market; historical inputs are never substituted')
        return run_live(args,model,optimizer,bridge,assembly_recipe)
    initial=deepcopy(bridge.paper_account.snapshot())
    native=pd.read_feather(args.root/"native_data/MacroHFT/df_val.feather")
    native.timestamp=pd.to_datetime(native.timestamp)
    last=bridge.paper_account.state["last_timestamp"]
    first=128 if not args.resume or not last else max(128,int((pd.Timestamp(last)-native.timestamp.iloc[0]).total_seconds()/60)+1)
    native=native.iloc[:min(len(native),first+(4096 if args.continuous else args.steps+2))].copy()
    market=native[["timestamp","open","high","low","close","volume"]].rename(columns={"timestamp":"date"})
    market["symbol"]="ETHUSDT";market["market"]="US";market["asset_class"]="crypto"
    stock=pd.read_csv(Path(__file__).resolve().parents[1]/"data/global_market_daily.csv")
    stock=stock[(stock.symbol=="AAPL")&(pd.to_datetime(stock.date)<native.timestamp.iloc[128])].tail(64)
    market=pd.concat([stock,market],ignore_index=True)
    panel=GlobalMarketPanel("native_ETHUSDT",raw_frame=market)
    panel.groups["ETHUSDT"]=("BINANCE_USDT","crypto")
    # Reuse the integer-unit paper engine with explicit crypto contract lots.
    # One simulated unit = 0.001 ETH; quote per unit = real ETH price / 1000.
    # Not a modified native model input: experts keep original ETH prices.
    eth_index=panel.symbols.index("ETHUSDT")
    panel.closes[:,eth_index]*=.001
    before_hash=parameter_digest(model.controller)
    initial_updates=model.optimizer_updates
    contexts={};rows=[];update_logs=[]
    # Expensive market experts run once for this short window. Native policy Q
    # and account-aware controller run every minute using the frozen market state.
    if first>=len(native):
        publish_worker(args.state,model,bridge,status="stopped",message="확보된 과거 시세 구간을 모두 처리했습니다.")
        return
    evidence=EvidenceJournal(args.state,cache_rows=args.rules['evidence_cache_rows'])
    if args.resume:
        if not evidence.load_contexts():evidence.migrate_legacy_contexts()
        contexts.update(evidence.load_contexts())
    inputs=market_inputs(args.root,native,first)
    market_packets=None
    tracker=dict(time=time.monotonic(),updates=model.optimizer_updates)
    step_count=len(native)-first if args.continuous else args.steps+2
    publish_worker(args.state,model,bridge,status="running",message="공식 ETHUSDT 과거 구간을 이어 실행합니다.")
    for step in range(step_count):
        modes=runtime_modes(args.state,args.rules)
        while args.continuous and not modes["observe_enabled"] and not (args.state/"stop.request").exists():
            latest=None
            if modes["learning_enabled"]:
                latest,logs=learn_saved_contexts(model,optimizer,bridge,contexts,args.rules)
                update_logs.extend(logs);update_logs=update_logs[-1:]
                save_contexts(args.state,contexts,evidence)
                if checkpoint_due(model,tracker,args.rules):
                    save_runtime(args,model,optimizer,bridge,contexts,evidence,assembly_recipe)
                    tracker=dict(time=time.monotonic(),updates=model.optimizer_updates)
            publish_worker(args.state,model,bridge,learning=latest,status="running",modes=modes,
                learning_active=latest is not None,message="새 판단 중지 · 저장 경험 학습 허용" if modes["learning_enabled"] else "새 판단·학습 중지 · 모델 메모리 유지")
            time.sleep(.25)
            modes=runtime_modes(args.state,args.rules)
        if args.continuous and (args.state/"stop.request").exists():break
        index=first+step;stamp=str(native.iloc[index].timestamp)
        pi=int(np.flatnonzero(panel.dates==np.datetime64(stamp))[0])
        if last and panel.dates[pi]<=np.datetime64(last):continue
        started=time.perf_counter();fills=bridge.advance(panel,pi,enabled=modes["paper_enabled"])
        decision=None;orders=None
        if args.continuous or step<args.steps:
            pstate,astate=bridge.paper_account.model_inputs(panel,pi)
            account=torch.tensor(np.column_stack([pstate,np.broadcast_to(astate,(len(pstate),len(astate)))]),dtype=torch.float32)[None]
            held=bool(bridge.paper_account.state["books"]["USD"]["positions"].get("ETHUSDT"))
            policy_data=model.macro_input_adapter(native,index,int(held))
            snapshot={"as_of":stamp,"symbols":panel.symbols,"currencies":{s:"USD" for s in panel.symbols},
                "tradable_symbols":[s for j,s in enumerate(panel.symbols) if panel.observed[pi,j]],
                "current_weights":{s:float(pstate[j][1]) for j,s in enumerate(panel.symbols)},"expert_inputs":{}}
            history=pd.read_csv(Path(__file__).resolve().parents[1]/'data/global_market_daily.csv')
            history=history[pd.to_datetime(history.date)<pd.Timestamp(stamp)]
            snapshot['stock_policy_history']=history.to_dict('records')
            book=bridge.paper_account.snapshot()['books']['USD']
            snapshot['policy_account']=dict(cash=book['cash'],nav=book['equity'],positions={s:p['quantity'] for s,p in book['positions'].items()})
            for key in model.controller.macro_policy_ids:snapshot["expert_inputs"][key]={**policy_data,"variant":model.experts[key].entry["variant"]}
            refresh_steps=max(1,min(assembly_recipe["refresh_seconds"][k] for k in model.controller.market_ids if k in assembly_recipe["enabled_experts"])//60) if assembly_recipe else max(1,int(args.rules['market_expert_refresh_seconds'])//60)
            if market_packets is None or (args.continuous and step%refresh_steps==0):
                inputs=market_inputs(args.root,native,index)
                snapshot["expert_inputs"].update(inputs)
                with torch.no_grad():decision,_=model(snapshot,account,device=args.device,explore=not getattr(model,"stable_policy",False))
                market_packets=[p for p in decision["raw_outputs"] if p["expert"] in model.controller.market_ids]
                evidence.save_market(market_packets)
            else:
                packets=list(market_packets)
                for key in model.controller.macro_policy_ids:
                    if assembly_recipe and key not in assembly_recipe["enabled_experts"]:continue
                    data=snapshot["expert_inputs"][key]
                    with registry_owner(model.gpu_lock,wait=True,on_wait=gpu_wait),model.scheduler.work("champion_live"):
                        packet=model.experts[key](model.root,data,args.device)
                    packet["expert"]=key;packet["native_features_verified"]=True
                    packets.append(packet)
                    if args.device.startswith("cuda"):torch.cuda.empty_cache()
                with torch.no_grad():decision,_=model(snapshot,account,packets=packets,explore=not getattr(model,"stable_policy",False))
            decision["native_decision_seconds"]=time.perf_counter()-started
            decision["current_weights"]=snapshot["current_weights"]
            orders=bridge.submit(decision,panel,pi,paper_executable=modes["paper_enabled"])
            contexts[str(panel.dates[pi])] = training_context(snapshot,decision)
        latest_learning=None
        if modes["learning_enabled"]:
            latest_learning,logs=learn_saved_contexts(model,optimizer,bridge,contexts,args.rules)
            update_logs.extend(logs)
        # Save once after this short continuous run, then acknowledge the rows.
        row={"timestamp":stamp,"decision":decision,"orders":orders,"fills":fills,
            "books":deepcopy(bridge.paper_account.snapshot()["books"]),"reward_points":bridge.paper_account.reward_points(),
            "seconds":time.perf_counter()-started,"replay_rows":bridge.replay.stats()["total"]}
        rows.append(row)
        if args.continuous:rows=rows[-2:]
        publish_paper_status(args.root,args.state,bridge,decision,row,model)
        save_contexts(args.state,contexts,evidence)
        evidence.record_cycle(row)
        if checkpoint_due(model,tracker,args.rules):
            save_runtime(args,model,optimizer,bridge,contexts,evidence,assembly_recipe)
            tracker=dict(time=time.monotonic(),updates=model.optimizer_updates)
        publish_worker(args.state,model,bridge,row,decision,latest_learning,status="running",modes=modes,learning_active=latest_learning is not None)
        last=str(panel.dates[pi])
        print(json.dumps({"step":step,"actions":decision["trading_output"]["actions"] if decision else None,
            "fills":fills,"NAV":row["books"]["USD"]["equity"],"updates":model.optimizer_updates,"seconds":row["seconds"]}),flush=True)
        if args.continuous:
            update_logs=update_logs[-1:]
            deadline=time.monotonic()+max(0,args.interval)
            while time.monotonic()<deadline and not (args.state/"stop.request").exists():time.sleep(min(.1,max(0,deadline-time.monotonic())))
    publish_worker(args.state,model,bridge,status="saving",stop_requested=True,message="계좌·replay·optimizer·TradingMoE.pt를 저장하는 중입니다.")
    finish_learning(model,optimizer,bridge,contexts)
    bridge.paper_account.save();save_contexts(args.state,contexts,evidence)
    save_runtime(args,model,optimizer,bridge,contexts,evidence,assembly_recipe)
    if rows:publish_paper_status(args.root,args.state,bridge,None,rows[-1],model,completed=True)
    publish_worker(args.state,model,bridge,status="stopped",stop_requested=False,message="저장 완료 · 다음 시작은 같은 계좌와 학습 상태에서 이어집니다.")
    if args.continuous:return
    report={"initial":initial["books"],"final":bridge.paper_account.snapshot()["books"],"fills":bridge.paper_account.state["fills"],
        "contract_units":{"ETHUSDT":{"quantity_per_unit":.001,"quote_currency":"USDT","USD_parity_assumption":True}},
        "steps":[{"timestamp":r["timestamp"],"seconds":r["seconds"],"actions":r["decision"]["trading_output"]["actions"] if r["decision"] else None,
                  "target_weights":r["decision"]["trading_output"]["target_weights"] if r["decision"] else None} for r in rows],
        "used_experts":rows[0]["decision"]["used_experts"] if rows and rows[0]["decision"] else [],
        "native_Q":[{p["expert"]:p["native_output"] for p in r["decision"]["raw_outputs"] if p["expert"].startswith("macrophft_")} for r in rows if r["decision"]],
        "updates":update_logs,"updated_parameter_groups":[g["name"] for g in groups],"expert_parameters_frozen":True,
        "optimizer_updates":model.optimizer_updates,"initial_optimizer_updates":initial_updates,"reward_points":bridge.paper_account.reward_points(),"replay":bridge.replay.stats(),
        "controller_before":before_hash,"controller_after":parameter_digest(model.controller),
        "parameters":sum(p.numel() for p in model.parameters()),"checkpoint_bytes":checkpoint.stat().st_size,
        "evidence_as_of":rows[0]["decision"]["evidence_as_of"] if rows and rows[0]["decision"] else {},
        "MarketGPT_context":"Real AAPL 2019 ITCH archival reference, not a contemporaneous 2023 ETH order book",
        "live_executable":False}
    atomic_json(args.state/"report.json",report)
    print(json.dumps({k:v for k,v in report.items() if k not in ("initial","final","native_Q","fills","steps","updates")}),flush=True)


def save_runtime(args,model,optimizer,bridge,contexts,evidence,assembly_recipe=None):
    retained=bridge.replay.unlearned_timestamps()|{item['timestamp'] for item in bridge.pending}
    # Discard only orphan contexts, never evidence for unlearned outcomes.
    for stamp in set(contexts)-retained:contexts.pop(stamp,None)
    bridge.paper_account.save();save_contexts(args.state,contexts,evidence)
    with model.resources.measure('checkpoint'):
        path=save_runtime_state(model,optimizer,args.checkpoint or TRADING_MOE_CHECKPOINT)
    if assembly_recipe:
        assembly_recipe['trainable_state']=str(path)
        atomic_json(args.recipe,assembly_recipe)
    bridge.replay.acknowledge_training({int(k):v for k,v in model.config.get("applied_replay_rows",{}).items()})
    evidence.save_contexts(contexts,checkpoint_saved=True)
    retained=set(contexts)|{item['timestamp'] for item in bridge.pending}
    model.config['applied_replay_contexts']={k:v for k,v in model.config.get('applied_replay_contexts',{}).items() if k in retained}
    model.config['applied_replay_rows']={}


def checkpoint_due(model,tracker,rules):
    return (time.monotonic()-tracker['time']>=float(rules['checkpoint_interval_seconds']) or
        model.optimizer_updates-tracker['updates']>=int(rules['checkpoint_every_updates']))


def run_live(args,model,optimizer,bridge,assembly_recipe=None):
    rules=getattr(args,'rules',None) or operating_rules(getattr(args,'settings',None))
    stream=LiveInputStream(args.market,bridge.paper_account.state['last_timestamp'])
    evidence=EvidenceJournal(args.state,cache_rows=rules['evidence_cache_rows'])
    contexts=evidence.load_contexts() if args.resume else {}
    from stockrl.moe_learner import AsyncLearner
    if not hasattr(model,'online_learner') and not getattr(model,'stable_policy',False):model.online_learner=AsyncLearner(model,optimizer,rules)
    completed=0
    tracker=dict(time=time.monotonic(),updates=model.optimizer_updates)
    market_cache={};last_market={}
    try:
        while not (args.state/'stop.request').exists():
            modes=runtime_modes(args.state,rules)
            item=stream.next_frame() if modes['observe_enabled'] else None
            latest=None
            if item is None:
                if modes['learning_enabled']:latest,_=learn_saved_contexts(model,optimizer,bridge,contexts,rules)
                save_contexts(args.state,contexts,evidence)
                if checkpoint_due(model,tracker,rules):
                    save_runtime(args,model,optimizer,bridge,contexts,evidence,assembly_recipe)
                    tracker=dict(time=time.monotonic(),updates=model.optimizer_updates)
                publish_worker(args.state,model,bridge,status='running',source_kind='live',modes=modes,
                    learning=latest,learning_active=latest is not None,message='새 완료 시세 대기',market_path=str(args.market))
                time.sleep(max(.1,args.interval))
                continue
            frame,stamp=item
            started=time.perf_counter()
            panel=GlobalMarketPanel(args.market,raw_frame=frame);index=len(panel.dates)-1
            fills=bridge.advance(panel,index,enabled=modes['paper_enabled'])
            # Fill changes holdings: rebuild the account-aware native input.
            with model.resources.measure('input_preparation'):
                panel,index,snapshot,account=live_snapshot(model,args.market,frame,stamp,bridge.paper_account,panel=panel)
            packets=[];reused=set();refreshed=False
            for key in [*model.controller.market_ids,*model.controller.macro_policy_ids]:
                if hasattr(model,'assembly_enabled') and key not in model.assembly_enabled:continue
                data=snapshot['expert_inputs'].get(key)
                if not data:continue
                cached=market_cache.get(key)
                age=(pd.Timestamp(stamp)-last_market[key]).total_seconds() if key in last_market else float('inf')
                interval=(assembly_recipe or {}).get('refresh_seconds',{}).get(key,rules['market_expert_refresh_seconds'])
                if cached and age<float(interval) and set(cached['symbols']).issubset(snapshot['symbols']):
                    packet=cached;reused.add(key)
                else:
                    with registry_owner(model.gpu_lock,wait=True,on_wait=getattr(model,'gpu_wait_callback',None)),model.scheduler.work('champion_live'):
                        chosen=model.resources.native_device(key,args.device,rules['native_vram_reserve_mib'])
                        with model.resources.measure('expert:'+key,chosen):
                            packet=model.experts[key](model.root,data,chosen)
                    packet.update(expert=key,native_features_verified=bool(data.get('native_features_verified')))
                    if key in model.controller.market_ids:
                        market_cache[key]=packet;last_market[key]=pd.Timestamp(stamp);refreshed=True
                packets.append(packet)
            if refreshed:
                with model.resources.measure('mmap_page_trim'):release_offloaded_pages()
            with torch.no_grad():decision,_=model(snapshot,torch.as_tensor(account,dtype=torch.float32),packets=packets,device=args.device,explore=not getattr(model,"stable_policy",False))
            for key in reused:decision['expert_status'][key]['status']='cached'
            evidence.save_market(list(market_cache.values()))
            decision.update(current_weights=snapshot['current_weights'],source_kind='live',market_path=str(args.market))
            executable=bool(decision['trading_output'].get('paper_executable'))
            if modes['paper_enabled'] and executable and bridge.collect_experience:
                contexts[str(panel.dates[index])]=training_context(snapshot,decision)
                save_contexts(args.state,contexts,evidence) # write evidence before order intent
            orders=bridge.submit(decision,panel,index,paper_executable=modes['paper_enabled'] and executable)
            if modes['learning_enabled']:latest,_=learn_saved_contexts(model,optimizer,bridge,contexts,rules)
            row=dict(timestamp=str(panel.dates[index]),decision=decision,orders=orders,fills=fills,
                books=bridge.paper_account.snapshot()['books'],reward_points=bridge.paper_account.reward_points(),
                seconds=time.perf_counter()-started,replay_rows=bridge.replay.stats()['total'])
            save_contexts(args.state,contexts,evidence);evidence.record_cycle(row)
            if checkpoint_due(model,tracker,rules):
                save_runtime(args,model,optimizer,bridge,contexts,evidence,assembly_recipe)
                tracker=dict(time=time.monotonic(),updates=model.optimizer_updates)
            publish_worker(args.state,model,bridge,row,decision,latest,status='running',source_kind='live',
                learning_active=latest is not None,modes=modes,input_status=snapshot['input_status'])
            completed+=1
            if not args.continuous and completed>=args.steps:break
    finally:
        finish_learning(model,optimizer,bridge,contexts)
        save_runtime(args,model,optimizer,bridge,contexts,evidence,assembly_recipe)
        publish_worker(args.state,model,bridge,status='stopped',source_kind='live',learning_active=False,
            stop_requested=False,message='실시간 계좌·학습 상태 저장 완료')


if __name__=="__main__":
    try:main()
    except Exception as exc:
        if worker_status_path:publish_worker(worker_status_path.parent,status="error",error=f"{type(exc).__name__}: {exc}")
        raise
