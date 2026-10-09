"""Publish a small model composition and carry learned slots across every revision."""
from pathlib import Path
import torch
from ..state_io import atomic_json,read_json
from .model_asset import load_moe_head
from .model_composition import split_context,compose_policy,atomic_torch_save,inherit_slots
from .policy import MoETrunk
from .checkpoint import Checkpoints
from .journal import Journal
from .experience_schema import can_extend,prepare_extension


def publish_header(settings,header,active,progress):
    path=settings.resolve(settings.expert_checkpoint)
    from .integrated_asset import read_header,integrate
    previous=read_header(path)
    layout_changed=(previous['config'].get('feature_sizes')!=header['config'].get('feature_sizes') or
                    previous['config'].get('stock_policy_ids')!=header['config'].get('stock_policy_ids') or
                    previous['config'].get('router_family')!='per-expert-context-v1')
    preserve=layout_changed and can_extend(previous,header)
    extension=None
    if preserve:
        staging=Journal(settings.state_dir/'operations.sqlite3')
        try:extension=prepare_extension(staging,previous,header)
        finally:staging.close()
    del previous
    ids=sorted(header['expert_mapping']);active=sorted(set(active))
    if not set(active).issubset(ids):raise ValueError('구성에 없는 Expert')
    header['active_experts']=active
    config=header['config'];config['router_family']='per-expert-context-v1'
    markets=sorted(k for k in ids if k not in config.get('stock_policy_ids',()))
    old_markets=sorted({k.split('.')[2] for k in header['state_dict'] if k.startswith('controller.router.')})
    original=split_context(header['state_dict'],old_markets)
    original=inherit_slots(original,header.get('slot_sources',{}),sorted({n.split('.')[1] for n in original if n.startswith('adapters.')}))
    spec=dict(expert_ids=ids,config={k:config[k] for k in ('feature_sizes','stock_policy_ids','assembly_routing','router_family','central') if k in config})
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(0);trunk=MoETrunk(spec)
    from .policy_transfer import transfer_state
    transfer_state(trunk,original)
    template=trunk.state_dict()
    header['state_dict']=template
    integrate(header,path,active,progress)
    partial=atomic_torch_save(header,path)
    selected,initial=load_moe_head(partial);selected['source_model']=str(path)
    selected['slot_sources']=header.get('slot_sources',{})
    selected['selection_revision']=read_json(settings.state_dir/'expert-library.json').get('selection_revision',0)
    checkpoints=Checkpoints(settings.state_dir/'policies',settings.resources.revisions)
    current=read_json(checkpoints.root/'current.json');records=list(checkpoints.revisions())
    prepared=[]
    # Validate migrations before changing the selected model or policy pointer.
    for index,record in enumerate(records):
        saved=torch.load(checkpoints.root/record['file'],map_location='cpu',weights_only=True)
        chosen={**selected,'active_experts':active if record['file']==current['file'] else
                [k for k in saved['model_spec'].get('active_experts',saved['expert_ids']) if k in ids]}
        actor,critic,optimizer=compose_policy(saved,chosen,settings.learning,initial)
        prepared.append((record,saved,actor,critic,optimizer))
        progress(stage='migrating',completed=index+1,total=len(records),detail='가중치와 optimizer 상태를 이름별로 이어받는 중')
    header.pop('frozen_experts',None)
    import gc
    gc.collect();partial.replace(path)
    checkpoints.retain=len(records)*2+1;published=None
    for record,saved,actor,critic,optimizer in prepared:
        latest=record['file']==current['file'];version=saved['version']+1 if latest else saved['version']
        if saved.get('torch_rng') is not None:torch.set_rng_state(saved['torch_rng'])
        replacement=checkpoints.save(actor,critic,optimizer,version,ids,optimizer_steps=saved.get('optimizer_steps',0),
            optimization_generation=saved.get('optimization_generation',saved['version']),publish=False)
        if latest:published=replacement
        old=checkpoints.root/record['file'];old.unlink(missing_ok=True);old.with_suffix('.json').unlink(missing_ok=True)
    if published:checkpoints.publish(published)
    journal=Journal(settings.state_dir/'operations.sqlite3')
    try:
        with journal.transaction():
            if layout_changed:
                if preserve:
                    rows,pending=extension
                    journal.db.executemany('UPDATE transitions SET payload=? WHERE id=?',rows)
                    for currency,value in pending.items():journal.replace_pending(currency,value)
                else:
                    journal.db.execute('UPDATE transitions SET learned=-1 WHERE learned IS NULL')
                    journal.db.execute('DELETE FROM pending')
            for key, in journal.db.execute('SELECT expert FROM evidence').fetchall():
                if key not in active:journal.db.execute('DELETE FROM evidence WHERE expert=?',(key,))
            account=journal.get_state('account')
            if account and layout_changed and not preserve:account['pending']={};journal.set_state('account',account)
            journal.set_state('decisions',[])
            metrics=journal.get_state('expert_metrics') or {}
            journal.set_state('expert_metrics',{k:v for k,v in metrics.items() if k in ids})
            journal.set_state('learning_metrics',{})
    finally:journal.close()
    settings.enabled_experts=active
    return published
