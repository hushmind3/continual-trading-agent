"""Frozen MoE registered in the official Stable-Baselines3 SAC Actor and Twin Critic."""
from __future__ import annotations
import torch
from torch import nn
from tensordict import TensorDict
import gymnasium as gym
import numpy as np
from stable_baselines3.sac.policies import SACPolicy
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from ..trading_moe import EvidenceAdapter
from .portfolio_network import PortfolioController,DEFAULT_NETWORK

INPUT_KEYS=['evidence','expert_mask','account','market','policy_q']
POLICY_FAMILY='sb3-sac-moe-v1'

class MoETrunk(nn.Module):
    def __init__(self,spec):
        super().__init__();cfg=spec['config'];self.expert_ids=spec['expert_ids'];self.active=set(spec.get('active_experts',self.expert_ids))
        self.slot_sources=spec.get('slot_sources',{})
        self.adapters=nn.ModuleDict({k:EvidenceAdapter(size) for k,size in cfg['feature_sizes'].items()})
        self.controller=PortfolioController(cfg['feature_sizes'],cfg.get('stock_policy_ids',[]),cfg.get('central'))
    def forward(self,evidence,mask,account,market,policy_q):
        values={k:evidence[k]*self.adapters[k].scale+self.adapters[k].bias for k in self.expert_ids}
        validity={k:mask[...,i] for i,k in enumerate(self.expert_ids)}
        return self.controller(values,validity,account,market,policy_q)

class MoEFeatures(BaseFeaturesExtractor):
    """Register the existing MoE as SB3's features extractor; no SAC algorithm here."""
    def __init__(self,space,spec):
        width=spec['config'].get('central',DEFAULT_NETWORK)['hidden_size']
        super().__init__(space,width+2);self.trunk=MoETrunk(spec)
    def forward(self,inputs):
        out=self.trunk({k:inputs['e_'+k][:,None] for k in self.trunk.expert_ids},
            inputs['expert_mask'][:,None].bool(),inputs['account'][:,None],inputs['market'][:,None],
            {k:inputs['q_'+k][:,None] for k in self.trunk.controller.policy_ids})
        return torch.cat([out['shared_latent'][:,0],out['allocation_scores'],out['cash_scores']],-1)


def spaces_for(spec):
    sizes=spec['config']['feature_sizes']
    shapes={'account':(16,),'market':(8,),'expert_mask':(len(spec['expert_ids']),),
        **{'e_'+k:(n,) for k,n in sizes.items()},
        **{'q_'+k:(4,) for k in spec['config'].get('stock_policy_ids',[])}}
    return gym.spaces.Dict({k:gym.spaces.Box(-np.inf,np.inf,shape=s,dtype=np.float32) for k,s in shapes.items()})


def asset_observations(obs,spec):
    return {'account':obs['account'],'market':obs['market'],'expert_mask':obs['expert_mask'].float(),
        **{'e_'+k:obs['evidence'][k] for k in spec['expert_ids']},
        **{'q_'+k:obs['policy_q'][k] for k in spec['config'].get('stock_policy_ids',[])}}


class RegisteredActor(nn.Module):
    def __init__(self,spec):
        super().__init__();self.model_spec={**spec,'policy_family':POLICY_FAMILY}
        self.backend=SACPolicy(spaces_for(spec),gym.spaces.Box(-1,1,(2,),dtype=np.float32),lambda _:0.0003,
            net_arch={'pi':[],'qf':[256,256]},features_extractor_class=MoEFeatures,
            features_extractor_kwargs={'spec':spec},share_features_extractor=True,normalize_images=False)
        # The official Actor starts from the retained allocation and cash opinions.
        with torch.no_grad():
            self.backend.actor.mu.weight.zero_();self.backend.actor.mu.bias.zero_()
            self.backend.actor.mu.weight[0,-2]=1;self.backend.actor.mu.weight[1,-1]=1
            self.backend.actor.log_std.weight.zero_();self.backend.actor.log_std.bias.fill_(-3)
        self.engine=None
    def forward(self,td,deterministic=False):
        inputs=asset_observations(td,self.model_spec)
        actions=self.backend.actor(inputs,deterministic=deterministic)
        td['action']=actions
        td['state_value']=torch.cat(self.backend.critic(inputs,actions),-1).mean().reshape(1)
        td['policy_family']=POLICY_FAMILY
        return td


class RegisteredCritic(nn.Module):
    def __init__(self,actor):
        super().__init__();self.network=actor.backend.critic;self.spec=actor.model_spec
    def forward(self,td):
        td['state_value']=torch.cat(self.network(asset_observations(td,self.spec),td['action']),-1).mean().reshape(1)
        return td


def build_policy(model_spec,initial_state=None):
    actor=RegisteredActor(model_spec);critic=RegisteredCritic(actor)
    import weakref
    actor._critic_ref=weakref.ref(critic)
    actor.backend.critic_target.requires_grad_(False)
    if initial_state is not None:
        from .policy_transfer import transfer_state
        transfer_state(actor.backend.actor.features_extractor.trunk,initial_state)
    return actor,critic


def parameters(actor,critic):
    return list({id(p):p for p in list(actor.parameters())+list(critic.parameters())}.values())

def parameter_names(actor,critic):
    seen=set();result=[]
    for prefix,module in [('',actor),('critic.',critic)]:
        for name,param in module.named_parameters():
            if id(param) in seen:continue
            seen.add(id(param));result.append((prefix+name,param))
    return result

def activate_policy(actor,critic,active):
    active=set(active);ids=set(actor.model_spec['expert_ids'])
    if not active.issubset(ids):raise ValueError('unregistered Expert slot')
    actor.model_spec['active_experts']=sorted(active)
    for module in actor.modules():
        if isinstance(module,MoETrunk):module.active=active
    for name,param in actor.named_parameters():
        parts=name.split('.');owners=set(parts)&ids
        param.requires_grad_(not owners or bool(owners&active))
        if not param.requires_grad:param.grad=None
    actor.backend.critic_target.requires_grad_(False)

def sparse_weights(logits):
    shifted=logits-logits.max(-1,keepdim=True).values;ordered=shifted.sort(-1,descending=True).values
    rank=torch.arange(1,ordered.shape[-1]+1,device=logits.device,dtype=logits.dtype);cumulative=ordered.cumsum(-1)
    support=1+rank*ordered>cumulative;count=support.sum(-1,keepdim=True).clamp_min(1)
    threshold=(cumulative.gather(-1,count-1)-1)/count
    return (shifted-threshold).clamp_min(0)

def observation(evidence,mask,account,market,policy_q):
    return TensorDict({'evidence':{k:torch.as_tensor(v,dtype=torch.float32) for k,v in evidence.items()},
        'expert_mask':torch.as_tensor(mask,dtype=torch.bool),'account':torch.as_tensor(account,dtype=torch.float32),
        'market':torch.as_tensor(market,dtype=torch.float32),'policy_q':{k:torch.as_tensor(v,dtype=torch.float32) for k,v in policy_q.items()}},batch_size=[])

@torch.no_grad()
def decide(actor,critic,obs,*,explore):
    obs=obs.to(next(actor.parameters()).device)
    with torch.autocast('cuda',dtype=torch.bfloat16,enabled=next(actor.parameters()).is_cuda):
        actor(obs,deterministic=not explore)
    actions=obs['action'].float()
    available=obs['expert_mask'].any(-1)
    scores=actions[:,0].masked_fill(~available,-1e6)
    cash=actions[available,1].mean() if available.any() else actions.new_tensor(1.)
    logits=torch.cat([scores,cash.reshape(1)])
    return sparse_weights(logits).cpu().numpy(),obs.detach().to('cpu').clone()


def migrate_policy(state,learning):
    from .model_composition import compose_policy
    return compose_policy(state,state['model_spec'],learning)
