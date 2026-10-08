"""Live/replay environment loop; Expert and learner work run out of this process."""
import argparse
import time
import numpy as np
import torch
from ..market_reader import IncrementalMarketCSV
from ..state_io import read_json
from ..state_io import atomic_json
from .config import load_settings, CONFIG_PATH
from .journal import Journal
from .checkpoint import Checkpoints
from .model_asset import load_moe_head,validate_source
from .policy import build_policy,migrate_policy,activate_policy,parameters
from .selection import selection
from .weights import PortfolioStrategy
from .environment import PortfolioEnvironment,market_view
from .worker_state import publish,stopped,control


def run(settings):
    torch.set_num_threads(settings.learning.cpu_threads)
    journal=Journal(settings.state_dir/"operations.sqlite3",settings.resources.journal_limit_mib,settings.resources.retained_transitions)
    checkpoints=Checkpoints(settings.state_dir/"policies",settings.resources.revisions)
    state,manifest=checkpoints.load()
    source_spec,original=load_moe_head(settings.resolve(settings.expert_checkpoint))
    if state is None and source_spec.get('source_format')=='registered_vertical_trading_moe_v2':
        header=torch.load(settings.resolve(settings.expert_checkpoint),map_location='cpu',weights_only=True)
        recovered=header.get('learned_policy')
        if recovered:
            recovered['model_spec']['source_model']=str(settings.resolve(settings.expert_checkpoint))
            actor,critic=build_policy(recovered['model_spec']);actor.load_state_dict(recovered['actor']);critic.load_state_dict(recovered['critic'])
            optimizer=torch.optim.AdamW(parameters(actor,critic),lr=settings.learning.learning_rate)
            if recovered.get('optimizer'):optimizer.load_state_dict(recovered['optimizer'])
            manifest=checkpoints.save(actor,critic,optimizer,recovered['version'],recovered['expert_ids'],
                optimizer_steps=recovered.get('optimizer_steps',0),optimization_generation=recovered.get('optimization_generation',recovered['version']))
            state=recovered
        del header
    if state:
        validate_source(state["model_spec"],source_spec)
        spec=state["model_spec"]
        spec['source_model']=str(settings.resolve(settings.expert_checkpoint))
        if spec.get('policy_family')!='sparse-normal-v2':
            actor,critic,optimizer=migrate_policy(state,settings.learning)
            manifest=checkpoints.save(actor,critic,optimizer,state['version']+1,state['expert_ids'],
                                      optimizer_steps=state.get('optimizer_steps',0))
            spec=actor.model_spec
            journal.event('policy','비중 0을 선택할 수 있는 정책으로 전환했습니다. 기존 학습 가중치와 optimizer 상태를 이어받았습니다.')
        else:
            actor,critic=build_policy(spec)
            actor.load_state_dict(state["actor"]); critic.load_state_dict(state["critic"])
    else:
        spec=source_spec
        actor,critic=build_policy(spec,original)
        manifest=checkpoints.save(actor,critic,None,0,spec["expert_ids"])
    selected_revision,selected=selection(settings,spec.get('active_experts',spec['expert_ids']))
    activate_policy(actor,critic,selected);actor.eval(); critic.eval()
    del original
    version=manifest["version"]
    generation=state.get('optimization_generation',version) if state else version
    environment=PortfolioEnvironment(settings,journal,spec)
    contract='sparse-separate-currency-portfolio-v4'
    if journal.get_state('execution_contract')!=contract:
        with journal.transaction():
            journal.db.execute('UPDATE transitions SET learned=-1 WHERE learned IS NULL')
            journal.db.execute('DELETE FROM pending')
            environment.pending.clear();environment.account.state['pending'].clear()
            journal.set_state('account',environment.account.state)
            journal.set_state('execution_contract',contract)
    strategy=PortfolioStrategy(actor,critic)
    reader=IncrementalMarketCSV(settings.state_dir/"live"/"market.csv",retain_timestamps=256)
    last=environment.account.state.get("last_timestamp")
    started_live=False
    decisions={d['symbol']:d for d in journal.get_state('decisions') or []}
    latest=list(decisions.values());last_decision=None
    try:
        publish(settings,"agent",status="ready",version=version,source_updates=spec["source_updates"],
                expert_count=len(selected),model=spec["source_model"],message="Champion MoE 학습 상태를 이어받았습니다.")
        while not stopped(settings,"agent"):
            revision,active=selection(settings,spec.get('active_experts',spec['expert_ids']))
            if revision!=selected_revision:
                activate_policy(actor,critic,active)
                decisions.clear();latest=[];last_decision=None;journal.set_state('decisions',[])
                selected_revision=revision
            publish(settings,'agent',selection_revision=selected_revision,rollout_generation=generation)
            current=read_json(checkpoints.root/"current.json")
            if current and current.get("file")!=manifest.get("file"):
                new,record=checkpoints.load()
                if new["model_spec"]["expert_ids"]!=spec["expert_ids"]:
                    raise ValueError("정책과 Expert 자산 구성이 다릅니다.")
                if new['model_spec'].get('policy_family')!='sparse-normal-v2':
                    actor,critic,optimizer=migrate_policy(new,settings.learning)
                    record=checkpoints.save(actor,critic,optimizer,new['version']+1,new['expert_ids'],
                                            optimizer_steps=new.get('optimizer_steps',0))
                    spec=actor.model_spec
                    manifest=record;version=record['version']
                    continue
                actor.load_state_dict(new["actor"]); critic.load_state_dict(new["critic"])
                manifest=record; version=record["version"];generation=new.get('optimization_generation',version)
            modes=control(settings)
            if not reader.path.exists():
                publish(settings,"agent",status="waiting",version=version,message="시세 입력 대기")
                time.sleep(1); continue
            frame,_=reader.refresh()
            if frame is None or frame.empty:
                time.sleep(1); continue
            view,frame=market_view(frame)
            if not len(view.dates):
                time.sleep(1); continue
            if last is None and not started_live and modes.get("mode","live")=="live":
                # A live start begins at the latest actual bar, not the first row of old history.
                indices=[len(view.dates)-1]
            else:
                indices=[i for i,stamp in enumerate(view.dates) if last is None or stamp>np.datetime64(last)]
            started_live=True
            packets={k:v for k,v in journal.evidence().items() if k in active}
            for index in indices:
                started=time.perf_counter(); stamp=str(view.dates[index])
                made_decision=False
                with journal.transaction():
                    fills=environment.advance(view,index,bool(modes.get("paper")))
                    for currency in ("KRW","USD"):
                        data=environment.observe(view,frame,index,currency,packets)
                        if data is None:
                            continue
                        environment.settle(data,generation)
                        if not data["coverage"]:
                            continue
                        data["explore"]=bool(modes.get("paper"))
                        result=strategy.generate_weights(data,target_date=stamp)
                        orders=environment.submit(result,data,view,index,generation,bool(modes.get("paper")))
                        targets=result.weights.weight.to_numpy(float)
                        journal.record_weights(currency,stamp,dict(zip(data["symbols"],targets.tolist())))
                        new_decisions=[dict(symbol=s,currency=currency,target_weight=float(target),current_weight=float(current),
                             action="BUY" if target-current>1e-5 else "SELL" if target-current < -1e-5 else "HOLD",as_of=stamp,
                             order_queued=s in {o.split('|')[-1] for o in orders})
                             for s,target,current in zip(data["symbols"],targets,data["current_weights"]) ]
                        decisions.update({d['symbol']:d for d in new_decisions});made_decision=True;last_decision=stamp
                    latest=list(decisions.values())
                    journal.set_state("account",environment.account.state)
                    journal.set_state('risk_peaks',environment.peak)
                    journal.set_state("decisions",latest)
                    for currency,book in environment.account.snapshot()["books"].items():
                        journal.record_nav(currency,stamp,book)
                    journal.record_fills(fills,environment.account.state['books'])
                last=stamp; reader.processed_through=stamp
                atomic_json({'last_timestamp':stamp},reader.path.parent/'agent'/'live_cursor.json')
                publish(settings,"agent",status="running" if made_decision else 'waiting',version=version,last_as_of=last_decision,market_cursor=stamp,
                        fills=fills[-20:],decision_seconds=time.perf_counter()-started,
                        checkpoint=manifest,source_updates=spec["source_updates"],expert_count=len(active))
            publish(settings,"agent",status="running" if latest else "waiting",version=version,last_as_of=last_decision,market_cursor=last,
                    message="새로운 완료 시세 대기" if not indices else None)
            time.sleep(0.5)
    finally:
        journal.close(); publish(settings,"agent",status="stopped")


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--config",default=str(CONFIG_PATH)); args=parser.parse_args()
    settings=load_settings(args.config)
    try:
        run(settings)
    except Exception as exc:
        publish(settings,"agent",status="error",error=f"{type(exc).__name__}: {exc}")
        raise
