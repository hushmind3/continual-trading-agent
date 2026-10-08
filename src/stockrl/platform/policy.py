"""TorchRL allocator initialized from the actual Champion MoE trainable state."""
from __future__ import annotations

import torch
from torch import nn
from torch.distributions import Dirichlet
from tensordict import TensorDict
from tensordict.nn import TensorDictModule
from torchrl.modules import ProbabilisticActor
from torchrl.envs.utils import set_exploration_type, ExplorationType
from ..trading_moe import EvidenceAdapter, VerticalController

INPUT_KEYS = ["evidence", "expert_mask", "account", "market", "policy_q"]


class MoETrunk(nn.Module):
    """Only trainable Champion modules. Frozen Expert bodies live in their own service."""
    def __init__(self, spec):
        super().__init__()
        config = spec["config"]
        self.expert_ids = spec["expert_ids"]
        self.adapters = nn.ModuleDict({k:EvidenceAdapter(size) for k,size in config["feature_sizes"].items()})
        self.controller = VerticalController(config["feature_sizes"],config.get("stock_policy_ids",()))
        if config.get("assembly_routing"):
            self.controller.assembly_routing = config["assembly_routing"]

    def forward(self, evidence, mask, account, policy_q):
        unbatched = account.ndim==2
        values = {k:evidence[k]*self.adapters[k].scale+self.adapters[k].bias for k in self.expert_ids}
        validity = {k:mask[...,i] for i,k in enumerate(self.expert_ids)}
        q = {k:policy_q[k] for k in self.controller.policy_ids}
        if unbatched:
            values={k:v.unsqueeze(0) for k,v in values.items()}
            validity={k:v.unsqueeze(0) for k,v in validity.items()}
            q={k:v.unsqueeze(0) for k,v in q.items()}; account=account.unsqueeze(0)
        output=self.controller(values,validity,account,q)
        return {k:v.squeeze(0) for k,v in output.items()} if unbatched else output


class Allocator(nn.Module):
    def __init__(self, trunk):
        super().__init__()
        self.trunk=trunk
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
        scores=scores.masked_fill(~output['coverage'],-20)
        logits=torch.cat([scores,cash],-1)
        concentration=logits.clamp(-20,20).softmax(-1)*20+0.01
        return concentration,output['value'].mean(-1,keepdim=True)


class Value(nn.Module):
    def __init__(self,trunk):
        super().__init__(); self.trunk=trunk

    def forward(self,evidence,expert_mask,account,market,policy_q):
        return self.trunk(evidence,expert_mask,account,policy_q)["value"].mean(-1,keepdim=True)


def build_policy(model_spec, initial_state=None):
    trunk=MoETrunk(model_spec)
    if initial_state is not None:
        trunk.load_state_dict(initial_state,strict=True)
    actor=ProbabilisticActor(
        TensorDictModule(Allocator(trunk),in_keys=INPUT_KEYS,out_keys=["concentration","state_value"]),
        in_keys=["concentration"],out_keys=["action"],distribution_class=Dirichlet,return_log_prob=True)
    critic=TensorDictModule(Value(trunk),in_keys=INPUT_KEYS,out_keys=["state_value"])
    actor.model_spec=model_spec
    return actor,critic


def parameters(actor,critic):
    # Actor and critic share the real Champion trunk; each parameter is optimized once.
    return list({id(p):p for p in list(actor.parameters())+list(critic.parameters())}.values())


def observation(evidence,mask,account,market,policy_q):
    return TensorDict({"evidence":{k:torch.as_tensor(v,dtype=torch.float32) for k,v in evidence.items()},
                       "expert_mask":torch.as_tensor(mask,dtype=torch.bool),
                       "account":torch.as_tensor(account,dtype=torch.float32),
                       "market":torch.as_tensor(market,dtype=torch.float32),
                       "policy_q":{k:torch.as_tensor(v,dtype=torch.float32) for k,v in policy_q.items()}},batch_size=[])


@torch.no_grad()
def decide(actor,critic,obs,*,explore):
    with set_exploration_type(ExplorationType.RANDOM if explore else ExplorationType.MEAN):
        actor(obs)
    return obs["action"].cpu().numpy(),obs.detach().clone()
