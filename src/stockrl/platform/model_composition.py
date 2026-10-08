"""Change Expert membership without resetting retained weights or Adam moments."""
from __future__ import annotations

import os
import torch

from .policy import build_policy, parameters


def atomic_torch_save(value, path):
    temporary=path.with_suffix('.partial')
    try:
        with temporary.open('wb') as stream:
            torch.save(value,stream);stream.flush();os.fsync(stream.fileno())
        return temporary
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def split_context(state,market_ids):
    """A Router context parameter belongs to one Expert; membership no longer sets its size."""
    result={}
    for name,value in state.items():
        suffix=next((s for s in ('router_context.weight','router_context.bias') if name.endswith(s)),None)
        if suffix:
            prefix=name.removesuffix(suffix)
            for index,key in enumerate(market_ids):
                result[prefix+'context_routers.'+key+'.'+suffix.split('.')[-1]]=value[index:index+1].clone()
        else:result[name]=value
    return result


def inherit_slots(values,sources,existing_ids):
    result=dict(values)
    for target,source in sources.items():
        if target in existing_ids:continue
        for name,value in values.items():
            parts=name.split('.')
            if source in parts:
                result['.'.join(target if part==source else part for part in parts)]=value
    return result


def compose_policy(saved,spec,learning,initial_state=None):
    """Preserve every retained slot and shared parameter; initialize only genuinely new slots."""
    family='sparse-normal-v2' if any(k.endswith('log_scale') for k in saved['actor']) else 'dirichlet-v1'
    old_market=sorted({name.split('.controller.router.',1)[1].split('.')[0] for name in saved['actor'] if '.controller.router.' in name})
    actor,critic=build_policy({**spec,'policy_family':family},initial_state,legacy=family=='dirichlet-v1')
    for module,values in ((actor,saved['actor']),(critic,saved['critic'])):
        prior=split_context(values,old_market) if spec['config'].get('router_family')=='per-expert-context-v1' else values
        prior=inherit_slots(prior,spec.get('slot_sources',{}),saved['expert_ids'])
        current=module.state_dict()
        for name,value in prior.items():
            if name not in current:continue
            if value.shape!=current[name].shape:raise ValueError('기존 슬롯의 입출력 크기가 바뀌었습니다: '+name)
            current[name]=value
        module.load_state_dict(current,strict=True)
    optimizer=torch.optim.AdamW(parameters(actor,critic),lr=learning.learning_rate)
    previous=saved.get('optimizer')
    if previous:
        groups=previous['param_groups'];names=list(saved['actor'])
        if len(groups)!=1 or len(groups[0]['params'])!=len(names):raise ValueError('optimizer 파라미터 순서가 다릅니다.')
        moments={name:previous['state'][i] for name,i in zip(names,groups[0]['params']) if i in previous['state']}
        transformed={}
        for name,values in moments.items():
            for key,value in values.items():
                if 'router_context.' in name:
                    prefix,suffix=name.split('router_context.',1)
                    for index,expert in enumerate(old_market):
                        target=prefix+'context_routers.'+expert+'.'+suffix
                        transformed.setdefault(target,{})[key]=value[index:index+1].clone() if torch.is_tensor(value) and value.ndim else value.clone() if torch.is_tensor(value) else value
                else:transformed.setdefault(name,{})[key]=value.clone() if torch.is_tensor(value) else value
        transformed=inherit_slots(transformed,spec.get('slot_sources',{}),saved['expert_ids'])
        for name,param in actor.named_parameters():
            if name in transformed:optimizer.state[param]={k:v.clone() if torch.is_tensor(v) else v for k,v in transformed[name].items()}
        optimizer.param_groups[0].update({k:v for k,v in groups[0].items() if k!='params'})
    from .policy import activate_policy
    activate_policy(actor,critic,spec.get('active_experts',spec['expert_ids']))
    return actor,critic,optimizer
