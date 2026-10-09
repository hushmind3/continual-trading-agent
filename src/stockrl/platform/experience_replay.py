"""Remap recorded Expert slots to the current MoE observation contract."""
import torch
from .journal import decode
from .policy import INPUT_KEYS


def compatible_observation(value,spec):
    source=sorted(value['evidence']);old_mask=value['expert_mask']
    if old_mask.shape[-1]!=len(source):raise ValueError('recorded Expert mask cannot be identified')
    ids=spec['expert_ids'];sizes=spec['config']['feature_sizes'];result={k:value[k] for k in INPUT_KEYS}
    mask=old_mask.new_zeros((*old_mask.shape[:-1],len(ids)));evidence={}
    for index,key in enumerate(ids):
        recorded=value['evidence'].get(key)
        if recorded is not None:
            if recorded.shape[-1]!=sizes[key]:raise ValueError('recorded Expert output shape changed: '+key)
            evidence[key]=recorded;mask[...,index]=old_mask[...,source.index(key)]
        else:evidence[key]=torch.zeros((*old_mask.shape[:-1],sizes[key]),dtype=torch.float32)
    result.update(evidence=evidence,expert_mask=mask,policy_q={k:value.get('policy_q',{}).get(k,torch.zeros((*old_mask.shape[:-1],4))) for k in spec['config'].get('stock_policy_ids',[])})
    return result


def compatible_transition(row,spec):
    result=compatible_observation(row,spec);result['action']=row['action']
    for key in ('loc','scale'):
        if key in row:result[key]=row[key]
    result['next']={**compatible_observation(row['next'],spec),**{k:row['next'][k] for k in ['reward','done','discount'] if k in row['next']}}

    return result
