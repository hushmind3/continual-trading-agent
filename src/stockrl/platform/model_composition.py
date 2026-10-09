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
    """Retain matching slots and widen saved tensors; new Qwen blocks initialize independently."""
    from .policy_transfer import transfer_state,transfer_optimizer
    from .portfolio_network import DEFAULT_NETWORK
    spec={**spec,'config':{**spec['config'],'central':{**DEFAULT_NETWORK,**spec['config'].get('central',{})}}}
    actor,critic=build_policy(spec,initial_state)
    old_market=sorted({n.split('.controller.router.',1)[1].split('.')[0] for n in saved['actor'] if '.controller.router.' in n})
    for module,values in ((actor,saved['actor']),(critic,saved['critic'])):
        previous=split_context(values,old_market)
        previous=inherit_slots(previous,spec.get('slot_sources',{}),saved.get('expert_ids',(saved.get('model_spec') or spec).get('expert_ids',[])))
        transfer_state(module,previous)
    if not any(k.startswith('backend.actor.') for k in saved['actor']):
        actor.backend.critic_target.load_state_dict(actor.backend.critic.state_dict())
    from .policy import activate_policy
    activate_policy(actor,critic,spec.get('active_experts',spec['expert_ids']))
    from .learner import register
    engine=register(actor,learning,'cpu',saved.get('sac'))
    if not saved.get('sac') and saved.get('optimizer'):
        from .policy_transfer import transfer_optimizer
        transfer_optimizer(saved,actor,engine.actor.optimizer,critic)
    return actor,critic,engine.actor.optimizer
