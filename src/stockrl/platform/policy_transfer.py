"""Import retained weights/Adam slices; old classifier execution is not retained."""
import torch


def previous_name(name):
    for prefix in ('backend.actor.features_extractor.trunk.','backend.critic.features_extractor.trunk.','backend.critic_target.features_extractor.trunk.'):
        if name.startswith(prefix):return 'module.0.module.trunk.'+name.removeprefix(prefix)
    if name.startswith('network.features_extractor.trunk.'):
        return 'module.trunk.'+name.removeprefix('network.features_extractor.trunk.')
    return name


def fit(value,template):
    result=template.clone()
    if value.ndim!=result.ndim:return result
    if not value.ndim:return value.clone()
    slices=tuple(slice(0,min(a,b)) for a,b in zip(value.shape,result.shape))
    result[slices]=value[slices];return result


def transfer_state(module,values):
    target=module.state_dict();copied=[]
    for name,template in target.items():
        old=name if name in values else previous_name(name)
        if old in values:
            target[name]=fit(values[old],template);copied.append((old,name))
    module.load_state_dict(target);return copied


def transfer_optimizer(saved,actor,optimizer,critic=None):
    previous=saved.get('optimizer')
    if not previous:return
    names=saved.get('optimizer_names',list(saved['actor']));groups=previous['param_groups']
    if len(groups)!=1 or len(groups[0]['params'])!=len(names):return
    moments={name:previous['state'].get(index,{}) for name,index in zip(names,groups[0]['params'])}
    from .policy import parameter_names
    current=parameter_names(actor,critic) if critic is not None else list(actor.named_parameters())
    for name,param in current:
        if name.startswith(('backend.critic.','backend.critic_target.')):continue
        inherited=name
        for target,source in actor.model_spec.get('slot_sources',{}).items():
            inherited=inherited.replace('.'+target+'.','.'+source+'.')
        old=next((n for n in (name,inherited,previous_name(name),previous_name(inherited)) if n in moments),None)
        if old is None:continue
        optimizer.state[param]={k:fit(v,torch.zeros_like(param)) if torch.is_tensor(v) and v.ndim else v.clone() if torch.is_tensor(v) else v for k,v in moments[old].items()}
