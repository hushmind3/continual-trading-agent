"""Official SAC.train and DictReplayBuffer, registered with the live MoE journal."""
import argparse
import time
import numpy as np
import torch
from stable_baselines3 import SAC
from stable_baselines3.common.logger import configure
from .config import load_settings,CONFIG_PATH
from .policy import build_policy,activate_policy,asset_observations,sparse_weights,POLICY_FAMILY
from .journal import Journal,decode
from .checkpoint import Checkpoints
from .worker_state import publish,stopped,control
from .experience_replay import compatible_transition


def register(actor,settings,device,saved=None):
    space=actor.backend.observation_space
    row_bytes=sum(np.prod(s.shape)*8 for s in space.spaces.values())+32
    capacity=min(settings.buffer_size,max(256,int(settings.replay_memory_mib*2**20/row_bytes)))
    import gymnasium as gym
    env=gym.Env()
    env.observation_space=space;env.action_space=actor.backend.action_space
    engine=SAC('MultiInputPolicy',env,learning_rate=settings.learning_rate,buffer_size=capacity,
        learning_starts=settings.minimum_batch_size,batch_size=settings.batch_size,
        tau=settings.tau,gamma=settings.discount,ent_coef=settings.entropy_coefficient,
        target_entropy='auto',target_update_interval=settings.target_update_interval,device=device,
        policy_kwargs={'net_arch':{'pi':[],'qf':[256,256]},'features_extractor_class':actor.backend.features_extractor_class,
            'features_extractor_kwargs':actor.backend.features_extractor_kwargs,'share_features_extractor':True,'normalize_images':False})
    engine.set_parameters({'policy':actor.backend.state_dict()},exact_match=False,device=device)
    actor.backend=engine.policy
    critic=actor._critic_ref() if hasattr(actor,'_critic_ref') else None
    if critic is not None:critic.network=engine.critic
    from .policy import activate_policy
    activate_policy(actor,critic or actor,actor.model_spec.get('active_experts',actor.model_spec['expert_ids']))
    engine.set_logger(configure(folder=None,format_strings=[]))
    if saved:
        restore_optimizers(engine,saved)
        with torch.no_grad():
            if engine.log_ent_coef is not None and saved.get('log_ent_coef') is not None:engine.log_ent_coef.copy_(saved['log_ent_coef'].to(device))
            elif engine.log_ent_coef is None and saved.get('ent_coef_tensor') is not None:engine.ent_coef_tensor.copy_(saved['ent_coef_tensor'].to(device))
        engine._n_updates=saved['updates']
    from .moe_session import optimizer_to
    for optimizer in [engine.actor.optimizer,engine.critic.optimizer,engine.ent_coef_optimizer]:
        if optimizer is not None:optimizer_to(optimizer,device)
    actor.engine=engine
    return engine


def restore_optimizers(engine,saved):
    from .policy_transfer import fit,previous_name
    for key,optimizer,module in [('actor.optimizer',engine.actor.optimizer,engine.actor),('critic.optimizer',engine.critic.optimizer,engine.critic)]:
        previous=saved['optimizers'].get(key)
        if not previous:continue
        names=saved.get('optimizer_names',{}).get(key)
        if names is None:
            optimizer.load_state_dict(previous);continue
        moments={name:previous['state'].get(index,{}) for name,index in zip(names,previous['param_groups'][0]['params'])}
        for name,param in module.named_parameters():
            if key=='critic.optimizer' and name.startswith('features_extractor.'):continue
            source_name=name
            if source_name not in moments:
                for target,source in engine.actor.features_extractor.trunk.slot_sources.items():
                    source_name=source_name.replace('.'+target+'.','.'+source+'.')
            if source_name in moments:
                optimizer.state[param]={k:fit(v,torch.zeros_like(param)) if torch.is_tensor(v) and v.ndim else v.clone() if torch.is_tensor(v) else v for k,v in moments[source_name].items()}
    if engine.ent_coef_optimizer is not None and saved['optimizers'].get('ent_coef_optimizer'):engine.ent_coef_optimizer.load_state_dict(saved['optimizers']['ent_coef_optimizer'])
    from .moe_session import optimizer_to
    for optimizer in [engine.actor.optimizer,engine.critic.optimizer,engine.ent_coef_optimizer]:
        if optimizer is not None:optimizer_to(optimizer,engine.device)


def training_state(actor):
    engine=actor.engine
    if engine is None:return getattr(actor,'sac_saved',None)
    return dict(optimizers={k:v for k,v in engine.get_parameters().items() if k!='policy'},
        optimizer_names={'actor.optimizer':[n for n,_ in engine.actor.named_parameters()],
            'critic.optimizer':[n for n,_ in engine.critic.named_parameters() if not n.startswith('features_extractor.')]},
        log_ent_coef=engine.log_ent_coef.detach() if engine.log_ent_coef is not None else None,
        ent_coef_tensor=engine.ent_coef_tensor if engine.log_ent_coef is None else None,updates=engine._n_updates)


def ingest(engine,journal,spec,cursor):
    rows=journal.db.execute('SELECT id,payload FROM transitions WHERE id>? AND (learned IS NULL OR learned>=0) ORDER BY id',(cursor,)).fetchall()
    accepted=[];rejected=0
    for identity,payload in rows:
        cursor=identity
        try:
            raw=decode(payload);row=compatible_transition(raw,spec);actions=row['action']
            if raw.get('policy_family')!=POLICY_FAMILY:
                if actions.ndim!=1:raise ValueError('unknown recorded action contract')
                # Exact action equivalence: sparsemax(weights) == original weights.
                weights=sparse_weights(actions)
                actions=torch.stack([weights[:-1],weights[-1].expand(len(weights)-1)],-1)
            if actions.shape!=(row['account'].shape[0],2):raise ValueError('invalid SAC action')
            before=asset_observations(row,spec);after=asset_observations(row['next'],spec)
            for index in torch.where(row['expert_mask'].any(-1))[0].tolist():
                engine.replay_buffer.add({k:v[index].numpy()[None] for k,v in before.items()},
                    {k:v[index].numpy()[None] for k,v in after.items()},actions[index].numpy()[None],
                    np.array([float(row['next']['reward'].item())],np.float32),
                    np.array([bool(row['next']['done'].item())]),[{}])
            accepted.append(identity)
        except (ValueError,KeyError,RuntimeError):rejected+=1
    return cursor,accepted,rejected


def run(settings,*,session=None):
    if session is None:torch.set_num_threads(settings.learning.cpu_threads)
    device=session.device if session else torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    stop=lambda:session.stopped('learner') if session else stopped(settings,'learner')
    journal=Journal(settings.state_dir/'operations.sqlite3',settings.resources.journal_limit_mib,settings.resources.retained_transitions)
    checkpoints=Checkpoints(settings.state_dir/'policies',settings.resources.revisions);checkpoints.defer_mirror=session is not None
    try:
        publish(settings,'learner',status='waiting_policy',device=str(device),engine='sb3-sac')
        while not stop():
            saved,manifest=checkpoints.load()
            if saved and saved['model_spec'].get('policy_family')==POLICY_FAMILY:break
            time.sleep(.5)
        else:return
        actor,critic=build_policy(saved['model_spec']);actor.load_state_dict(saved['actor']);critic.load_state_dict(saved['critic'])
        activate_policy(actor,critic,saved['model_spec'].get('active_experts',saved['expert_ids']));actor.to(device);critic.to(device)
        engine=register(actor,settings.learning,device,saved.get('sac'))
        version=saved['version'];prior_steps=saved.get('optimizer_steps',0)-engine._n_updates
        cursor=0;last_update=0.;replay_path=checkpoints.root/'replay.pkl';meta_path=replay_path.with_suffix('.json')
        from ..state_io import read_json,atomic_json
        meta=read_json(meta_path)
        if replay_path.exists() and meta.get('expert_packages')==saved['model_spec'].get('expert_packages') and meta.get('family')==POLICY_FAMILY:
            engine.load_replay_buffer(replay_path);cursor=meta['cursor']
        rejected=0
        while not stop():
            cursor,ids,invalid=ingest(engine,journal,actor.model_spec,cursor);rejected+=invalid
            if ids:
                temporary=replay_path.with_suffix('.tmp');engine.save_replay_buffer(temporary);temporary.replace(replay_path)
                atomic_json(dict(cursor=cursor,expert_packages=saved['model_spec'].get('expert_packages'),family=POLICY_FAMILY),meta_path)
                journal.acknowledge(ids,version)
            count=engine.replay_buffer.size();required=settings.learning.minimum_batch_size
            replay=journal.stats();replay.update(ready=count,batch_ready=count,groups=[dict(ready=count,oldest_created=0)],engine='sb3-sac',incompatible=rejected)
            publish(settings,'learner',status='waiting_batch',device=str(device),engine='sb3-sac',version=version,
                optimizer_steps=prior_steps+engine._n_updates,replay=replay,
                next_update_at=time.time()+max(0,settings.learning.checkpoint_seconds-(time.monotonic()-last_update)),
                message=f'SB3 Replay Buffer {count}/{required}개 · Actor와 Twin Q 사용')
            if count<required or not control(settings).get('learning',True) or time.monotonic()-last_update<settings.learning.checkpoint_seconds:
                time.sleep(.5);continue
            started=time.perf_counter();publish(settings,'learner',status='training',samples=settings.learning.batch_size)
            engine.train(gradient_steps=settings.learning.gradient_steps,batch_size=settings.learning.batch_size)
            if not all(torch.isfinite(p).all() for p in actor.parameters()):raise FloatingPointError('SAC update contains non-finite parameters')
            version+=1;steps=prior_steps+engine._n_updates
            record=checkpoints.save(actor,critic,None,version,saved['expert_ids'],optimizer_steps=steps,optimization_generation=version)
            seconds=time.perf_counter()-started;last_update=time.monotonic();measured=engine.logger.name_to_value
            metrics=dict(version=version,optimizer_steps=steps,loss=float(measured['train/actor_loss']),
                actor_loss=float(measured['train/actor_loss']),critic_loss=float(measured['train/critic_loss']),entropy_coefficient=float(measured['train/ent_coef']),
                samples=settings.learning.batch_size*settings.learning.gradient_steps,seconds=seconds,
                samples_per_second=settings.learning.batch_size*settings.learning.gradient_steps/max(seconds,1e-9),
                replay_size=count,replay_capacity=engine.replay_buffer.buffer_size,updated_at=time.time(),engine='sb3-sac',checkpoint=record)
            journal.set_state('learning_metrics',metrics);publish(settings,'learner',status='updated',**metrics,last_update=metrics)
            journal.event('learning',f'SAC v{version} · 공식 Replay {count}개 · 업데이트 {settings.learning.gradient_steps}회')
    finally:journal.close();publish(settings,'learner',status='stopped')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',default=str(CONFIG_PATH));args=parser.parse_args()
    settings=load_settings(args.config)
    try:run(settings)
    except Exception as exc:
        publish(settings,'learner',status='error',error=f'{type(exc).__name__}: {exc}');raise
