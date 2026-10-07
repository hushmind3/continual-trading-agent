"""Immutable evaluation snapshots and reversible publication of learned MoE state."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid
import torch

from .state_io import atomic_json
from .operating_rules import operating_rules


def trainable_path(checkpoint):
    checkpoint=Path(checkpoint)
    return checkpoint.with_name(checkpoint.stem+'.trainable.pt')


def checkpoint_identity(checkpoint):
    path=Path(checkpoint);stat=path.stat()
    return dict(name=path.name,bytes=stat.st_size,mtime_ns=stat.st_mtime_ns)


def file_digest(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def frozen_signature(config,entries):
    # Pins the registered originals/architectures without copying or rehashing GBs.
    value=dict(sizes=config['feature_sizes'],counts=config.get('native_module_counts'),
        experts={k:{field:e.get(field) for field in ('backend','variant','files','checkpoint_sha256','stock_policy')}
            for k,e in sorted(entries.items())})
    def encode(v):
        if isinstance(v,bytes):return hashlib.sha256(v).hexdigest()
        raise TypeError(type(v).__name__)
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=encode).encode()).hexdigest()


def save_state(state,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.partial')
    try:
        torch.save(state,temporary)
        temporary.replace(path)
    finally:temporary.unlink(missing_ok=True)


def source_token(checkpoint):
    path=trainable_path(checkpoint)
    return dict(checkpoint=checkpoint_identity(checkpoint),state_sha256=file_digest(path) if path.is_file() else None)


def training_state(checkpoint):
    checkpoint=Path(checkpoint);small=trainable_path(checkpoint)
    if small.is_file():
        state=torch.load(small,map_location='cpu',weights_only=True)
        if state.get('source_checkpoint')!=checkpoint_identity(checkpoint):
            raise ValueError('learned state belongs to another checkpoint; saved work was not overwritten')
        return state
    saved=torch.load(checkpoint,map_location='cpu',weights_only=True,mmap=True)
    if saved.get('format')!='registered_vertical_trading_moe_v1':raise ValueError('unknown MoE checkpoint')
    return dict(format='trading_moe_assembly_v1',feature_sizes=saved['config']['feature_sizes'],
        controller={k.removeprefix('controller.'):v.clone() for k,v in saved['state_dict'].items() if k.startswith('controller.')},
        adapters={k.removeprefix('adapters.'):v.clone() for k,v in saved['state_dict'].items() if k.startswith('adapters.')},
        optimizer=deepcopy(saved.get('optimizer_state')),optimizer_updates=saved.get('optimizer_updates',0),
        learning_state={k:saved['config'][k] for k in ('replay_account_episode','applied_replay_rows','applied_replay_contexts') if k in saved['config']},
        assembly_config={k:saved['config'][k] for k in ('assembly_enabled_experts','assembly_routing') if k in saved['config']},
        frozen_signature=frozen_signature(saved['config'],saved['expert_mapping']),source_checkpoint=checkpoint_identity(checkpoint))


def load_runtime_state(model,checkpoint):
    path=trainable_path(checkpoint)
    if not path.is_file():return None
    state=training_state(checkpoint)
    if state['frozen_signature']!=frozen_signature(model.config,{k:e.entry for k,e in model.experts.items()}):
        raise ValueError('runtime state differs from registered frozen experts')
    return model.load_assembly_state(path)


def save_runtime_state(model,optimizer,checkpoint):
    path=trainable_path(checkpoint)
    model.save_assembly_state(path,optimizer,source_checkpoint=checkpoint_identity(checkpoint))
    return path


def snapshot_pair(champion,candidate,directory,candidate_recipe=None):
    directory=Path(directory);receipt={}
    for role,checkpoint in (('champion',champion),('candidate',candidate)):
        before=source_token(checkpoint);state=training_state(checkpoint)
        if source_token(checkpoint)!=before:raise ValueError(role+' changed while its evaluation snapshot was captured')
        if role=='candidate' and candidate_recipe:
            configuration=state.get('assembly_config',{})
            enabled=configuration.get('assembly_enabled_experts',list(state['feature_sizes']))
            routing=configuration.get('assembly_routing',dict(market=dict(top_k=0,temperature=1.),policy=dict(top_k=0,temperature=1.)))
            if (set(enabled)!=set(candidate_recipe['enabled_experts']) or
                routing!=dict(market=candidate_recipe['market_routing'],policy=candidate_recipe['policy_routing'])):
                raise ValueError('requested recipe differs from the actual trained Candidate; register that configuration first')
        path=directory/(role+'.pt');save_state(state,path)
        receipt[role]=dict(path=str(path.resolve()),sha256=file_digest(path),source=str(Path(checkpoint).resolve()),
            source_token=before,optimizer_updates=state['optimizer_updates'],frozen_signature=state['frozen_signature'])
    if receipt['champion']['frozen_signature']!=receipt['candidate']['frozen_signature']:
        raise ValueError('the pair does not share the same frozen experts and native schemas')
    return receipt


def promote(champion,result,rollback_root):
    rules=operating_rules()
    pair=result.get('evaluation_states',{})
    paper=result.get('scores',{}).get('paper',{})
    if (result.get('state')!='qualified' or set(pair)!= {'champion','candidate'} or paper.get('delta',0)<=float(rules['promotion_min_delta']) or
        paper.get('candidate',{}).get('net_return',0)<=float(rules['promotion_min_return']) or
        paper.get('candidate',{}).get('max_drawdown',float('inf'))>paper.get('champion',{}).get('max_drawdown',0)+float(rules['promotion_drawdown_tolerance'])):
        raise ValueError('verified learned-state evaluation and passing paper scores are required')
    for role,record in pair.items():
        if file_digest(record['path'])!=record['sha256']:raise ValueError(role+' evaluation snapshot changed')
        if source_token(record['source'])!=record['source_token']:raise ValueError(role+' learned state changed after evaluation; reevaluate')
    if pair['champion']['frozen_signature']!=pair['candidate']['frozen_signature']:
        raise ValueError('frozen expert identity differs')
    if Path(pair['champion']['source']).resolve()!=Path(champion).resolve():raise ValueError('evaluation belongs to another Champion')
    previous=training_state(champion)
    winner=torch.load(pair['candidate']['path'],map_location='cpu',weights_only=True)
    backup=Path(rollback_root)/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8])
    backup.mkdir(parents=True)
    old=backup/'champion.trainable.pt';save_state(previous,old)
    winner=deepcopy(winner)
    # Replay row IDs are local to the Candidate DB. They must never consume
    # Champion experiences with coincidentally equal IDs.
    winner['candidate_learning_lineage']=deepcopy(winner.get('learning_state',{}))
    winner['learning_state']={}
    winner['source_checkpoint']=checkpoint_identity(champion)
    save_state(winner,trainable_path(champion))
    receipt=dict(backup=str(old.resolve()),backup_sha256=file_digest(old),
        installed_sha256=file_digest(trainable_path(champion)),winner=pair['candidate'],checkpoint=str(Path(champion).resolve()))
    atomic_json(receipt,backup/'promotion.json')
    return receipt


def rollback(champion,receipt):
    if Path(receipt['checkpoint']).resolve()!=Path(champion).resolve():raise ValueError('rollback belongs to another Champion')
    if file_digest(receipt['backup'])!=receipt['backup_sha256']:raise ValueError('rollback backup is damaged')
    previous=torch.load(receipt['backup'],map_location='cpu',weights_only=True)
    if previous['source_checkpoint']!=checkpoint_identity(champion):raise ValueError('original frozen Champion checkpoint changed')
    save_state(previous,trainable_path(champion))
    return trainable_path(champion)
