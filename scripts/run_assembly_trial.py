"""One existing Candidate worker, one shared frozen base, paired paper trials.

Actual stored native market evidence is replayed without relabeling its as-of.
MacroHFT Q inputs are recomputed from official ETH features and EACH book's action.
Only learned head/adapters are saved; no full checkpoint save or expert training.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import numpy as np
import pandas as pd
import torch
from stockrl.assembly_orchestrator import read
from stockrl.expert_registry import atomic_json
from stockrl.expert_system import registry_owner
from stockrl.market_panel import GlobalMarketPanel
from stockrl.moe_paper import TradingMoEPaper
from stockrl.trading_moe import TradingMoE
from stockrl.paths import PROJECT_ROOT, PROJECT_TRASH_DIR
from stockrl.moe_live import live_snapshot,daily_history
from stockrl.moe_promotion import snapshot_pair,file_digest
from stockrl.operating_rules import operating_rules,RULES_PATH
from stockrl.state_io import EvidenceJournal, append_log, WorkerLog, retire_trial_debug
from run_native_vertical_trading import publish_worker, release_offloaded_pages


def cached_rows(settings=None):
    rules=settings or operating_rules()
    minimum=int(rules['evaluation_min_observations']);maximum=int(rules['evaluation_max_observations'])
    """Bounded tail, not a full runtime journal scan."""
    stores=sorted((PROJECT_ROOT/"runtime").glob("**/evidence.sqlite3"),key=lambda p:p.stat().st_mtime,reverse=True)
    for path in stores:
        if "assembly" in path.parts:continue
        rows=[row for row in EvidenceJournal(path.parent).cached_rows() if row.get("decision")]
        if len(rows)>=minimum:return rows[-maximum:],str(path)
    files=list((PROJECT_ROOT/"runtime").glob("**/cycles.jsonl"))
    files=sorted((p for p in files if "assembly" not in p.parts),key=lambda p:p.stat().st_mtime,reverse=True)
    for path in files:
        rows=[]
        with path.open("rb") as handle:
            handle.seek(max(0,path.stat().st_size-16*1024**2))
            for line in handle.read().splitlines():
                try:row=json.loads(line)
                except ValueError:continue
                decision=row.get("decision") or {}
                if decision.get("raw_outputs") and decision.get("trading_output"):
                    rows.append(row)
        rows=sorted({r["timestamp"]:r for r in rows}.values(),key=lambda r:r["timestamp"])
        if len(rows)>=minimum:return rows[-maximum:],str(path)
    raise ValueError(f'실제 native 출력 cache가 {minimum}시점 이상 필요합니다.')


def evaluate(args,model,recipe,phase,rows,native,panel,state_file):
    model.load_assembly_state(state_file)
    # Every pair starts from the same fresh capital. Reusing a Champion book
    # from an earlier candidate would skip bars and lose its measured drawdown.
    side="candidate" if recipe["candidate_id"]==args.candidate_id else "champion"
    directory=args.state/"assembly"/args.candidate_id/side/phase
    # Restart interrupted trials from their real saved books; no operational reset.
    bridge=TradingMoEPaper(directory,settings=getattr(args,'rules',None))
    initial=bridge.paper_account.state["books"]["USD"]["initial_cash"]
    progress_file=directory/"progress.json"
    progress=read(progress_file)
    peak=progress.get("peak",initial);drawdown=progress.get("drawdown",0)
    seconds=progress.get("seconds",0);decisions=progress.get("decisions",0)
    used=set(progress.get("used_experts",[]))
    def save_progress():
        atomic_json(progress_file,{"peak":peak,"drawdown":drawdown,"seconds":seconds,
            "decisions":decisions,"used_experts":sorted(used)})
    for row in rows:
        if (args.state/"stop.request").exists():raise InterruptedError("사용자가 시험을 정지했습니다.")
        stamp=row["timestamp"]
        index=int(np.flatnonzero(panel.dates==np.datetime64(stamp))[0])
        if bridge.paper_account.state.get("last_timestamp") and np.datetime64(stamp)<=np.datetime64(bridge.paper_account.state["last_timestamp"]):continue
        started=time.perf_counter()
        bridge.advance(panel,index)
        pstate,astate=bridge.paper_account.model_inputs(panel,index)
        account=torch.tensor(np.column_stack([pstate,np.broadcast_to(astate,(len(pstate),len(astate)))]),dtype=torch.float32)[None]
        held=bool(bridge.paper_account.state["books"]["USD"]["positions"].get("ETHUSDT"))
        packets=[]
        for packet in row["decision"]["raw_outputs"]:
            if packet['expert'] in model.controller.policy_ids:continue
            if hasattr(model,'assembly_enabled') and packet['expert'] not in model.assembly_enabled:continue
            age=(pd.Timestamp(stamp)-pd.Timestamp(packet["as_of"])).total_seconds()
            if age<0:raise ValueError("cache에 미래 시점 출력이 있습니다.")
            if age>max(recipe["refresh_seconds"].get(packet["expert"],7200),packet.get('sampling_seconds') or 0):continue
            packets.append(packet)
        snapshot={"as_of":stamp,"symbols":panel.symbols,"currencies":{s:"USD" for s in panel.symbols},
            "tradable_symbols":[s for j,s in enumerate(panel.symbols) if panel.observed[index,j]],
            "current_weights":{s:float(pstate[j][1]) for j,s in enumerate(panel.symbols)},"expert_inputs":{}}
        if native is None:
            _,_,snapshot,_=live_snapshot(model,args.evaluation_market,
                args.evaluation_frame.loc[args.evaluation_frame.date<=pd.Timestamp(stamp)],pd.Timestamp(stamp),bridge.paper_account,
                daily_frame=args.evaluation_daily)
            # Keep the common evaluation symbol axis, even if later symbols
            # first arrive midway through the immutable quote interval.
            snapshot.update(symbols=panel.symbols,currencies={s:__import__('stockrl.paper_account',fromlist=['_currency'])._currency(*panel.groups[s]) or 'USD' for s in panel.symbols},
                current_weights={s:float(pstate[j][1]) for j,s in enumerate(panel.symbols)},
                tradable_symbols=[s for j,s in enumerate(panel.symbols) if panel.observed[index,j]])
            native_inputs=snapshot['expert_inputs']
        else:
            native_index=int(np.flatnonzero(native.timestamp==pd.Timestamp(stamp))[0])
            policy_data=model.macro_input_adapter(native,native_index,int(held))
            native_inputs={key:{**policy_data,'variant':model.experts[key].entry['variant']} for key in model.controller.macro_policy_ids}
            history=pd.read_csv(PROJECT_ROOT/'data/global_market_daily.csv')
            snapshot['stock_policy_history']=history[pd.to_datetime(history.date)<=pd.Timestamp(stamp)].to_dict('records')
            book=bridge.paper_account.snapshot()['books']['USD']
            snapshot['policy_account']=dict(cash=book['cash'],nav=book['equity'],positions={s:p['quantity'] for s,p in book['positions'].items()})
        for key in model.controller.macro_policy_ids:
            if (hasattr(model,'assembly_enabled') and key not in model.assembly_enabled) or key not in native_inputs:continue
            with registry_owner(model.gpu_lock,wait=True),model.scheduler.work('candidate_live'):
                packet=model.experts[key](model.root,native_inputs[key],args.device)
            packet.update(expert=key,native_features_verified=True);packets.append(packet)
        with torch.no_grad():decision,_=model(snapshot,account,packets=packets,device=args.device,explore=False)
        decision["current_weights"]=snapshot["current_weights"]
        bridge.submit(decision,panel,index,paper_executable=True)
        books=bridge.paper_account.snapshot()['books']
        book={'equity':initial*bridge.paper_account.normalized_equity()/len(books),
            'net_pnl':sum(b['net_pnl']/b['initial_cash'] for b in books.values())*initial/len(books)}
        peak=max(peak,book["equity"]);drawdown=max(drawdown,1-book["equity"]/peak)
        decisions+=1;seconds+=time.perf_counter()-started
        used.update(p["expert"] for p in packets)
        save_progress()
        publish_worker(args.state,model,bridge,decision=decision,status="running",evaluation_stage=phase,
            evaluation_role=side,assembly_candidate_id=args.candidate_id,message=phase+" · "+recipe["candidate_id"],learning_active=False,
            selected_experts=decision["used_experts"])
        append_log(directory/"decisions.jsonl",{"timestamp":stamp,"trading_output":decision["trading_output"],"NAV":book["equity"],
                "used_experts":sorted(used),"reward":bridge.paper_account.reward_points()})
    # One actual later bar matures orders/reward under the same fee engine.
    last=rows[-1]["timestamp"]
    after=np.flatnonzero(panel.dates>np.datetime64(last))
    if len(after) and (not bridge.paper_account.state.get("last_timestamp") or
            panel.dates[int(after[0])]>np.datetime64(bridge.paper_account.state["last_timestamp"])):
        bridge.advance(panel,int(after[0]))
    books=bridge.paper_account.snapshot()['books']
    book=dict(equity=initial*bridge.paper_account.normalized_equity()/len(books),
        net_pnl=sum(b['net_pnl']/b['initial_cash'] for b in books.values())*initial/len(books),
        trade_count=sum(b['trade_count'] for b in books.values()),
        fees=sum(b['fees']/b['initial_cash'] for b in books.values())*initial/len(books),
        slippage=sum(b.get('slippage',0)/b['initial_cash'] for b in books.values())*initial/len(books))
    drawdown=max(drawdown,1-book["equity"]/max(peak,book["equity"]))
    save_progress()
    return {"initial_NAV":initial,"final_NAV":book["equity"],"net_return":book["equity"]/initial-1,
        "pnl":book["net_pnl"],"trades":book["trade_count"],"fees":book["fees"],
        "slippage":book.get("slippage",0),"max_drawdown":drawdown,"seconds":seconds,
        "decisions":decisions,"reward":bridge.paper_account.reward_points(),"replay":bridge.replay.stats(),
        "used_experts":sorted(used),"first_as_of":rows[0]["timestamp"],"last_as_of":last}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,required=True);parser.add_argument("--checkpoint",type=Path,required=True)
    parser.add_argument("--state",type=Path,required=True);parser.add_argument("--assembly-root",type=Path,required=True)
    parser.add_argument('--evaluation-states',type=Path)
    parser.add_argument('--settings',type=Path,default=RULES_PATH)
    parser.add_argument("--device",default="cuda:0");parser.add_argument("--interval",type=float)
    parser.add_argument("--resume",action="store_true");parser.add_argument("--continuous",action="store_true")
    args=parser.parse_args();args.state.mkdir(parents=True,exist_ok=True)
    args.rules=operating_rules(args.settings)
    sys.stdout=sys.stderr=WorkerLog(args.state/"activity.log")
    recipe=read(args.assembly_root/"current_recipe.json");champion=read(args.assembly_root/"champion_recipe.json")
    args.candidate_id=recipe["candidate_id"]
    result_file=args.assembly_root/"results"/(args.candidate_id+".json");result_file.parent.mkdir(exist_ok=True)
    result={"candidate_id":args.candidate_id,"state":"blocked","scores":{}}
    try:
        torch.set_num_threads(4)
        publish_worker(args.state,status="loading",evaluation_stage="replay",assembly_candidate_id=args.candidate_id,error=None)
        rows,source=cached_rows(args.rules)
        minutes={pd.Timestamp(row['timestamp']).floor('min') for row in rows}
        if len(minutes)<int(args.rules['validation_min_market_minutes']):
            raise ValueError(f"평가에 실제 관측 {args.rules['validation_min_market_minutes']}분이 필요합니다. 현재 {len(minutes)}분입니다.")
        snapshots=args.assembly_root/'evaluation'/args.candidate_id
        receipt=read(args.evaluation_states) if args.evaluation_states else snapshot_pair(args.checkpoint,
            args.checkpoint.with_name('candidate.pt'),snapshots,recipe)
        for record in receipt.values():
            if file_digest(record['path'])!=record['sha256']:raise ValueError('evaluation state hash mismatch')
        result['evaluation_states']=receipt
        market_ages={}
        for row in rows:
            for packet in row["decision"]["raw_outputs"]:
                if packet["expert"].startswith("macrophft_"):continue
                age=(pd.Timestamp(row["timestamp"])-pd.Timestamp(packet["as_of"])).total_seconds()
                if age>=0:market_ages.setdefault(packet["expert"],set()).add(age)
        result["evaluation_context"]={"symbols":["ETHUSDT"],
            "market_ages":{key:sorted(ages) for key,ages in market_ages.items()}}
        # Decode only the small trained modules and six real native policy bodies.
        # All eight large market expert bodies stay in their shared file/cache.
        model,_=TradingMoE.load_checkpoint(args.checkpoint,cached_market=True)
        if args.device.startswith("cuda") and not torch.cuda.is_available():raise ValueError("CUDA를 사용할 수 없습니다.")
        model.set_learning_device(args.device);release_offloaded_pages()
        champion_state=receipt['champion']['path']
        candidate_state=Path(receipt['candidate']['path'])
        result["trainable_state"]=str(candidate_state)
        result["small_state_bytes"]=candidate_state.stat().st_size
        if rows[0]['decision'].get('source_kind')=='live':
            paths={r['decision'].get('market_path') for r in rows}
            if len(paths)!=1:raise ValueError('evaluation rows mix different live environments')
            args.evaluation_market=Path(paths.pop())
            args.evaluation_frame=pd.read_csv(args.evaluation_market)
            args.evaluation_frame.date=pd.to_datetime(args.evaluation_frame.date,utc=True).dt.tz_convert(None)
            args.evaluation_daily=daily_history(args.evaluation_market,pd.Timestamp(rows[-1]['timestamp'])+pd.Timedelta(days=1))
            panel=GlobalMarketPanel(args.evaluation_market,raw_frame=args.evaluation_frame)
            native=None
            result['evaluation_context']['symbols']=panel.symbols
        else:
            native=pd.read_feather(args.root/"native_data/MacroHFT/df_val.feather")
            native.timestamp=pd.to_datetime(native.timestamp)
            market=native[["timestamp","open","high","low","close","volume"]].rename(columns={"timestamp":"date"})
            market["symbol"]="ETHUSDT";market["market"]="US";market["asset_class"]="crypto"
            stocks=pd.read_csv(PROJECT_ROOT/"data/global_market_daily.csv")
            stocks=stocks[(stocks.symbol=="AAPL")&(pd.to_datetime(stocks.date)<pd.Timestamp(rows[0]["timestamp"]))].tail(64)
            panel=GlobalMarketPanel("assembly_ETHUSDT",raw_frame=pd.concat([stocks,market],ignore_index=True))
            panel.groups["ETHUSDT"]=("BINANCE_USDT","crypto");panel.closes[:,panel.symbols.index("ETHUSDT")]*=.001
        split=max(1,min(len(rows)-1,int(len(rows)*float(args.rules['evaluation_replay_fraction']))))
        stages=[("replay",rows[:split]),("paper",rows[split:])]
        for phase,interval in stages:
            champion_score=evaluate(args,model,champion,phase,interval,native,panel,champion_state)
            candidate_score=evaluate(args,model,recipe,phase,interval,native,panel,candidate_state)
            delta=candidate_score["net_return"]-champion_score["net_return"]
            result["scores"][phase]={"champion":champion_score,"candidate":candidate_score,"delta":delta,"source":source}
            if not np.isfinite(delta):raise ValueError("평가값이 유한하지 않습니다.")
            if phase=="replay" and delta<-float(args.rules['replay_rejection_tolerance']):
                result.update(state="rejected",reason="replay 예선: Champion 대비 -0.10%p 미만")
                break
        else:
            compared=result["scores"]["paper"]
            passes=compared["delta"]>float(args.rules['promotion_min_delta']) and compared["candidate"]["net_return"]>float(args.rules['promotion_min_return']) and compared["candidate"]["max_drawdown"]<=compared["champion"]["max_drawdown"]+float(args.rules['promotion_drawdown_tolerance'])
            result.update(state="qualified" if passes else "rejected",
                reason="분리된 paper 구간 비용 차감 비교 통과" if passes else "paper 비교: 양수 수익·Champion 초과·손실폭 조건 미충족")
        result["evaluation_note"]="고정된 실제 Champion/Candidate 학습 state · 동일 시장/초기자본/체결비용 · 해당 시험계좌로 정책 재계산 · 탐험 OFF · 평가 중 학습 없음"
    except InterruptedError as exc:result.update(state="paused",reason=str(exc))
    except Exception as exc:result.update(state="blocked",reason=f"{type(exc).__name__}: {exc}")
    result["completed_at"]=datetime.now(timezone.utc).isoformat()
    atomic_json(result_file,result)
    if result["state"] in ("qualified","rejected"):
        retire_trial_debug(args.state/"assembly"/args.candidate_id,
            PROJECT_TRASH_DIR/"trial-diagnostics"/args.candidate_id)
    publish_worker(args.state,status="stopped",evaluation_stage=result["state"],message=result.get("reason"),error=None,
        assembly_candidate_id=args.candidate_id,small_state_bytes=result.get("small_state_bytes",0),checkpoint_copies=0)
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=="__main__":main()
