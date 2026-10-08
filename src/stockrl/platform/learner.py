"""TorchRL clipped PPO in an independent CPU process, with crash-safe publication."""
import argparse
import math
import time
import torch
from tensordict import TensorDict
from torchrl.data import LazyTensorStorage, SamplerWithoutReplacement, TensorDictReplayBuffer
from torchrl.objectives import ClipPPOLoss

from .config import load_settings, CONFIG_PATH
from .policy import build_policy, parameters,activate_policy
from .journal import Journal
from .checkpoint import Checkpoints
from .worker_state import publish, stopped, control
from .selection import selection,acknowledge
from ..state_io import read_json


def learn_batch(actor, critic, optimizer, rows, cfg):
    batch = torch.stack([TensorDict(row, batch_size=[]) for row in rows])
    with torch.no_grad():
        critic(batch["next"])
        discount=batch.get(('next','discount'),cfg.discount)
        target = batch["next","reward"] + discount * (~batch["next","done"]).float() * batch["next","state_value"]
        batch["value_target"] = target
        batch["advantage"] = target-batch["state_value"]
    buffer = TensorDictReplayBuffer(storage=LazyTensorStorage(len(batch)),
                                  sampler=SamplerWithoutReplacement(), batch_size=min(16,len(batch)))
    buffer.extend(batch)
    loss_module = ClipPPOLoss(actor,critic,functional=False,clip_epsilon=cfg.clip_epsilon,
                             entropy_coeff=cfg.entropy_coefficient/batch['action'].shape[-1],normalize_advantage=True)
    losses, steps = [], 0
    for _ in range(cfg.epochs):
        for _ in range(math.ceil(len(batch)/min(16,len(batch)))):
            loss = loss_module(buffer.sample())
            objective = loss["loss_objective"]+loss["loss_critic"]+loss["loss_entropy"]
            if not torch.isfinite(objective):
                raise ValueError("학습 손실이 유효하지 않아 정책을 발행하지 않았습니다.")
            optimizer.zero_grad(set_to_none=True)
            objective.backward()
            torch.nn.utils.clip_grad_norm_(parameters(actor,critic),1.0,error_if_nonfinite=True)
            optimizer.step()
            losses.append(float(objective.detach()))
            steps += 1
    return sum(losses)/len(losses), steps


def run(settings):
    torch.set_num_threads(settings.learning.cpu_threads)
    journal = Journal(settings.state_dir/"operations.sqlite3",settings.resources.journal_limit_mib,settings.resources.retained_transitions)
    checkpoints = Checkpoints(settings.state_dir/"policies",settings.resources.revisions)
    try:
        publish(settings,"learner",status="waiting_policy",device="cpu",message="정책 복원·변환 대기")
        while not stopped(settings,"learner"):
            state, manifest = checkpoints.load()
            if state and state['model_spec'].get('policy_family')=='sparse-normal-v2':
                break
            time.sleep(1)
        else:
            return
        state['model_spec']['source_model']=str(settings.resolve(settings.expert_checkpoint))
        actor,critic = build_policy(state["model_spec"])
        actor.load_state_dict(state["actor"]); critic.load_state_dict(state["critic"])
        activate_policy(actor,critic,state['model_spec'].get('active_experts',state['expert_ids']))
        optimizer = torch.optim.AdamW(parameters(actor,critic),lr=settings.learning.learning_rate)
        if state.get("optimizer"):
            optimizer.load_state_dict(state["optimizer"])
        if state.get("torch_rng") is not None:
            torch.set_rng_state(state["torch_rng"])
        version, steps = state["version"], state.get("optimizer_steps",0)
        generation=state.get('optimization_generation',version)
        selected_revision=state.get('model_spec',{}).get('selection_revision',0)
        journal.acknowledge(state.get("applied_ids",[]),version)
        metrics=journal.get_state("learning_metrics") or {}
        if metrics.get("version")==version:
            publish(settings,"learner",**metrics)
        last_update = 0.;next_update_at=0.
        while not stopped(settings,"learner"):
            revision,active=selection(settings,state['model_spec'].get('active_experts',state['expert_ids']))
            if revision!=selected_revision:
                if read_json(settings.state_dir/'workers'/'agent.json').get('selection_revision',-1)<revision:
                    time.sleep(.2);continue
                activate_policy(actor,critic,active);actor.model_spec['selection_revision']=revision
                version+=1;checkpoints.save(actor,critic,optimizer,version,state['expert_ids'],optimizer_steps=steps,optimization_generation=generation)
                selected_revision=revision;acknowledge(settings,revision)
            counts = journal.stats(generation,settings.learning.max_policy_lag)
            publish(settings,"learner",status="waiting_batch",version=version,optimizer_steps=steps,replay=counts,device="cpu",
                    message=f"같은 종목 구성의 학습 경험 {counts['batch_ready']}/{settings.learning.batch_size}개",next_update_at=next_update_at)
            if not control(settings).get("learning",True) or time.monotonic()-last_update < settings.learning.checkpoint_seconds:
                time.sleep(1)
                continue
            ids, rows = journal.batch(generation,settings.learning.max_policy_lag,settings.learning.batch_size)
            if not ids:
                time.sleep(1)
                continue
            started = time.perf_counter()
            publish(settings,"learner",status="training",samples=len(rows))
            loss, updates = learn_batch(actor,critic,optimizer,rows,settings.learning)
            version += 1; steps += updates;generation+=1
            record = checkpoints.save(actor,critic,optimizer,version,state["expert_ids"],ids,optimizer_steps=steps,optimization_generation=generation)
            journal.acknowledge(ids,generation)
            seconds = time.perf_counter()-started
            metrics=dict(version=version,optimizer_steps=steps,loss=loss,seconds=seconds,
                         samples=len(rows),samples_per_second=len(rows)/max(seconds,1e-9),checkpoint=record)
            journal.set_state("learning_metrics",metrics)
            publish(settings,"learner",status="updated",**metrics)
            journal.event("learning",f"정책 버전 {version} · 경험 {len(rows)}개 학습 완료")
            last_update = time.monotonic()
            next_update_at=time.time()+settings.learning.checkpoint_seconds
    finally:
        journal.close()
        publish(settings,"learner",status="stopped")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--config",default=str(CONFIG_PATH))
    args=parser.parse_args()
    settings=load_settings(args.config)
    try:
        run(settings)
    except Exception as exc:
        publish(settings,"learner",status="error",error=f"{type(exc).__name__}: {exc}")
        raise
