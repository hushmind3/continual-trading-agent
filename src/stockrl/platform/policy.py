"""TorchRL allocator initialized from the actual Champion MoE trainable state."""
from __future__ import annotations

import torch
from torch import nn
from torch.distributions import Dirichlet
from tensordict import TensorDict
from tensordict.nn import TensorDictModule
from torchrl.modules import ProbabilisticActor,IndependentNormal
from torchrl.envs.utils import set_exploration_type, ExplorationType
from ..trading_moe import EvidenceAdapter, VerticalController

INPUT_KEYS = ["evidence", "expert_mask", "account", "market", "policy_q"]


class MoETrunk(nn.Module):
    """Trainable Champion modules, fed by the same process's frozen Expert stage."""
    def __init__(self, spec):
        super().__init__()
        config = spec["config"]
        self.expert_ids = spec["expert_ids"]
        self.active=set(spec.get('active_experts',self.expert_ids))
        self.adapters = nn.ModuleDict({k:EvidenceAdapter(size) for k,size in config["feature_sizes"].items()})
        self.controller = VerticalController(config["feature_sizes"],config.get("stock_policy_ids",()),
            config.get('router_family')=='per-expert-context-v1')
        if config.get("assembly_routing"):
            self.controller.assembly_routing = config["assembly_routing"]

    def forward(self, evidence, mask, account, policy_q):
        unbatched = account.ndim==2
        values = {k:evidence[k]*self.adapters[k].scale+self.adapters[k].bias for k in self.expert_ids}
        # Availability is recorded in each observation. Replay must retain the mask
        # under which its action was taken, including Experts disabled afterwards.
        validity = {k:mask[...,i] for i,k in enumerate(self.expert_ids)}
        q = {k:policy_q[k] for k in self.controller.policy_ids}
        if unbatched:
            values={k:v.unsqueeze(0) for k,v in values.items()}
            validity={k:v.unsqueeze(0) for k,v in validity.items()}
            q={k:v.unsqueeze(0) for k,v in q.items()}; account=account.unsqueeze(0)
        output=self.controller(values,validity,account,q)
        return {k:v.squeeze(0) for k,v in output.items()} if unbatched else output


class Allocator(nn.Module):
    def __init__(self, trunk, legacy=False):
        super().__init__()
        self.trunk=trunk
        self.legacy=legacy
        if not legacy:self.log_scale=nn.Parameter(torch.tensor(-3.912023))
        self.adjustment=nn.Sequential(nn.Linear(72,64),nn.SiLU(),nn.Linear(64,1))
        self.cash_adjustment=nn.Linear(64,1)
        for head in (self.adjustment[-1],self.cash_adjustment):
            nn.init.zeros_(head.weight); nn.init.zeros_(head.bias)

    def forward(self,evidence,expert_mask,account,market,policy_q):
        output=self.trunk(evidence,expert_mask,account,policy_q)
        latent=output["shared_latent"]
        # The allocator reuses the learned heads on the real 64D latent.
        # Frozen policy target=0 is evidence, not a hard prohibition on RL exploration.
        scores=self.trunk.controller.market_fusion.allocation(latent).squeeze(-1)+self.adjustment(torch.cat([latent,market],-1)).squeeze(-1)
        cash=self.trunk.controller.market_fusion.cash(latent.mean(-2))+self.cash_adjustment(latent.mean(-2))
        scores=scores.masked_fill(~output['coverage'],-20 if self.legacy else -1000000)
        logits=torch.cat([scores,cash],-1)
        if self.legacy:
            return logits.clamp(-20,20).softmax(-1)*20+0.01,output['value'].mean(-1,keepdim=True)
        active=torch.cat([output['coverage'],torch.ones_like(cash,dtype=torch.bool)],-1)
        scale=torch.where(active,self.log_scale.exp().clamp(0.0001,2),torch.ones_like(logits))
        return logits,scale,output['value'].mean(-1,keepdim=True)


class Value(nn.Module):
    def __init__(self,trunk):
        super().__init__(); self.trunk=trunk

    def forward(self,evidence,expert_mask,account,market,policy_q):
        return self.trunk(evidence,expert_mask,account,policy_q)["value"].mean(-1,keepdim=True)


def build_policy(model_spec, initial_state=None, *, legacy=False):
    trunk=MoETrunk(model_spec)
    if initial_state is not None:
        trunk.load_state_dict(initial_state,strict=True)
    module=TensorDictModule(Allocator(trunk,legacy),in_keys=INPUT_KEYS,
        out_keys=["concentration","state_value"] if legacy else ['loc','scale','state_value'])
    actor=ProbabilisticActor(module,in_keys=['concentration'] if legacy else ['loc','scale'],out_keys=['action'],
        distribution_class=Dirichlet if legacy else IndependentNormal,return_log_prob=True)
    critic=TensorDictModule(Value(trunk),in_keys=INPUT_KEYS,out_keys=["state_value"])
    actor.model_spec={**model_spec,'policy_family':'dirichlet-v1' if legacy else 'sparse-normal-v2'}
    return actor,critic


def parameters(actor,critic):
    # Actor and critic share the real Champion trunk; each parameter is optimized once.
    return list({id(p):p for p in list(actor.parameters())+list(critic.parameters())}.values())


def activate_policy(actor,critic,active):
    active=set(active);ids=set(actor.model_spec['expert_ids'])
    if not active.issubset(ids):raise ValueError('등록되지 않은 Expert 슬롯')
    actor.model_spec['active_experts']=sorted(active)
    for module in actor.modules():
        if isinstance(module,MoETrunk):module.active=active
    for name,param in actor.named_parameters():
        parts=name.split('.');owned=set()
        for index,part in enumerate(parts[:-1]):
            if part in ('adapters','router','context_routers','policy_adapters','policy_router','projections') and parts[index+1] in ids:
                owned.add(parts[index+1])
        param.requires_grad_(not owned or bool(owned.intersection(active)))
        if not param.requires_grad:param.grad=None


def sparse_weights(logits):
    shifted=logits-logits.max(-1,keepdim=True).values
    ordered=shifted.sort(-1,descending=True).values
    rank=torch.arange(1,ordered.shape[-1]+1,device=logits.device,dtype=logits.dtype)
    cumulative=ordered.cumsum(-1)
    support=1+rank*ordered>cumulative
    count=support.sum(-1,keepdim=True).clamp_min(1)
    threshold=(cumulative.gather(-1,count-1)-1)/count
    return (shifted-threshold).clamp_min(0)


def migrate_policy(state,learning):
    """Keep learned MoE/allocator weights and Adam moments when adding sparse allocation."""
    old_actor,old_critic=build_policy(state['model_spec'],legacy=True)
    old_actor.load_state_dict(state['actor']);old_critic.load_state_dict(state['critic'])
    actor,critic=build_policy(state['model_spec'])
    result=actor.load_state_dict(state['actor'],strict=False)
    if result.unexpected_keys or any(not k.endswith('log_scale') for k in result.missing_keys):
        raise ValueError('이전 정책의 가중치 구성이 예상과 다릅니다.')
    critic.load_state_dict(state['critic'])
    optimizer=torch.optim.AdamW(parameters(actor,critic),lr=learning.learning_rate)
    if state.get('optimizer'):
        old_optimizer=torch.optim.AdamW(parameters(old_actor,old_critic),lr=learning.learning_rate)
        old_optimizer.load_state_dict(state['optimizer'])
        new=dict(actor.named_parameters());old=dict(old_actor.named_parameters())
        for name,parameter in old.items():
            if parameter in old_optimizer.state:
                optimizer.state[new[name]]={k:v.clone() if torch.is_tensor(v) else v for k,v in old_optimizer.state[parameter].items()}
    return actor,critic,optimizer


def observation(evidence,mask,account,market,policy_q):
    return TensorDict({"evidence":{k:torch.as_tensor(v,dtype=torch.float32) for k,v in evidence.items()},
                       "expert_mask":torch.as_tensor(mask,dtype=torch.bool),
                       "account":torch.as_tensor(account,dtype=torch.float32),
                       "market":torch.as_tensor(market,dtype=torch.float32),
                       "policy_q":{k:torch.as_tensor(v,dtype=torch.float32) for k,v in policy_q.items()}},batch_size=[])


@torch.no_grad()
def decide(actor,critic,obs,*,explore):
    obs=obs.to(next(actor.parameters()).device)
    with set_exploration_type(ExplorationType.RANDOM if explore else ExplorationType.MEAN):
        actor(obs)
    weights=obs['action'] if actor.model_spec.get('policy_family')=='dirichlet-v1' else sparse_weights(obs['action'])
    # Only the compact action and durable experience leave the GPU pipeline.
    return weights.cpu().numpy(),obs.detach().to('cpu').clone()
