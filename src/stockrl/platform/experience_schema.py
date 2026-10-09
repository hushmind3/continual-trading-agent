"""Add unavailable market slots to stored observations without inventing Expert outputs."""
import torch
from .journal import decode,encode


def can_extend(previous,current):
    old=previous['config'];new=current['config']
    return (old.get('router_family')=='per-expert-context-v1' and
        set(old.get('stock_policy_ids',[])).issubset(new.get('stock_policy_ids',[])) and
        all(k not in old['feature_sizes'] for k in set(new.get('stock_policy_ids',[]))-set(old.get('stock_policy_ids',[]))) and
        all(new['feature_sizes'].get(k)==size for k,size in old['feature_sizes'].items()))


def extend_observation(value,old_ids,new_ids,feature_sizes,stock_ids=()):
    value=dict(value);old_mask=value['expert_mask']
    if old_mask.shape[-1]!=len(old_ids):raise ValueError('저장된 경험의 Expert 마스크 크기가 다릅니다.')
    mask=old_mask.new_zeros((*old_mask.shape[:-1],len(new_ids)))
    for index,key in enumerate(old_ids):mask[...,new_ids.index(key)]=old_mask[...,index]
    value['expert_mask']=mask;value['evidence']=dict(value['evidence'])
    for key,size in feature_sizes.items():
        if key not in value['evidence']:value['evidence'][key]=torch.zeros((*old_mask.shape[:-1],size),dtype=torch.float32)
    value['policy_q']=dict(value.get('policy_q',{}))
    for key in stock_ids:
        if key not in value['policy_q']:value['policy_q'][key]=torch.zeros((*old_mask.shape[:-1],4),dtype=torch.float32)
    return value


def prepare_extension(journal,previous,current):
    old_ids=sorted(previous['expert_mapping']);new_ids=sorted(current['expert_mapping']);sizes=current['config']['feature_sizes']
    def transition(value):
        result=extend_observation(value,old_ids,new_ids,sizes,current['config'].get('stock_policy_ids',[]))
        if 'next' in value:result['next']=extend_observation(value['next'],old_ids,new_ids,sizes,current['config'].get('stock_policy_ids',[]))
        return result
    rows=[(encode(transition(decode(payload))),identity) for identity,payload in journal.db.execute('SELECT id,payload FROM transitions WHERE learned IS NULL')]
    pending={currency:{**value,'transition':transition(value['transition'])} for currency,value in journal.pending().items()}
    return rows,pending
