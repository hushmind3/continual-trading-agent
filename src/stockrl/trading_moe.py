"""Reusable trainable evidence adapters and the shared 64D financial controller."""
import numpy as np
import torch
from torch import nn
from .expert_system import adapter_features,build_fusion_head


class EvidenceAdapter(nn.Module):
    def __init__(self,size):
        super().__init__()
        self.scale=nn.Parameter(torch.ones(size))
        self.bias=nn.Parameter(torch.zeros(size))
    def forward(self,packet,symbols):
        row=adapter_features([packet],symbols)[0]
        x=np.asarray(row["features"],np.float32)
        scale=np.maximum(np.sqrt(np.mean(x.astype(np.float64)**2,axis=-1,keepdims=True)),1e-6)
        meta=np.column_stack([np.log1p(scale[:,0]),np.full(len(x),np.log1p(row["horizon"])),
                             np.full(len(x),np.log1p(row["sampling_seconds"] or 0))])
        values=np.concatenate([x/scale,meta],axis=-1).astype(np.float32)
        mask=np.asarray(row["coverage_mask"],bool);values[~mask]=0
        return torch.from_numpy(values[None]).to(self.scale.device)*self.scale+self.bias,torch.from_numpy(mask[None]).to(self.scale.device)


class VerticalController(nn.Module):
    def __init__(self,sizes,stock_policy_ids=(),per_expert_context=False):
        super().__init__()
        self.stock_policy_ids=list(stock_policy_ids)
        self.market_ids=sorted(k for k in sizes if k not in self.stock_policy_ids)
        self.policy_ids=self.stock_policy_ids
        self.sizes=sizes
        self.router=nn.ModuleDict({k:nn.Linear(sizes[k],1) for k in self.market_ids})
        self.per_expert_context=per_expert_context
        if per_expert_context:self.context_routers=nn.ModuleDict({k:nn.Linear(16,1) for k in self.market_ids})
        else:self.router_context=nn.Linear(16,len(self.market_ids))
        self.market_fusion=build_fusion_head({k:sizes[k] for k in self.market_ids})
        self.policy_adapters=nn.ModuleDict({k:nn.Linear(sizes[k],64) for k in self.policy_ids})
        self.policy_attention=nn.MultiheadAttention(64,4,batch_first=True)
        if self.stock_policy_ids:
            self.policy_router=nn.ModuleDict({k:nn.Linear(sizes[k],1) for k in self.policy_ids})
            # Equal initial preferences; training may learn symbol/context-specific preferences.
            for router in self.policy_router.values():
                nn.init.zeros_(router.weight);nn.init.zeros_(router.bias)
        self.account_context=nn.Linear(16,64)
        self.controller_norm=nn.LayerNorm(64)
        # New residual heads start neutral; retained trained heads are restored.
        for head in (self.market_fusion.policy,self.market_fusion.allocation,self.market_fusion.cash):
            nn.init.zeros_(head.weight);nn.init.zeros_(head.bias)

    def forward(self,evidence,validity,account,policy_q=None):
        context=torch.cat([self.context_routers[k](account) for k in self.market_ids],-1) if self.per_expert_context else self.router_context(account)
        logits=torch.cat([self.router[k](evidence[k]) for k in self.market_ids],-1)+context
        market_mask=torch.stack([validity[k] for k in self.market_ids],-1)
        routing=getattr(self,"assembly_routing",{})
        logits=logits/max(.05,float(routing.get("market",{}).get("temperature",1)))
        top_k=int(routing.get("market",{}).get("top_k",0))
        if 0<top_k<len(self.market_ids):
            selected=torch.zeros_like(market_mask).scatter_(-1,logits.masked_fill(~market_mask,-1e9).topk(top_k,-1).indices,True)
            market_mask=market_mask&selected
        gates=logits.masked_fill(~market_mask,-1e9).softmax(-1)*market_mask
        gates=gates/gates.sum(-1,keepdim=True).clamp_min(1e-9)
        # Every available historical expert participates; no initial fixed top-2.
        gates=.95*gates+.05*market_mask/market_mask.sum(-1,keepdim=True).clamp_min(1)
        fused=self.market_fusion({k:evidence[k] for k in self.market_ids},account,
            key_padding_mask=~market_mask,allow_untrained=True,expert_gates=gates*market_mask.sum(-1,keepdim=True))
        latent=fused["shared_latent"]
        if not self.policy_ids:
            final=self.controller_norm(latent+self.account_context(account))
            head=self.market_fusion
            return {**fused,"policy_logits":head.policy(final),"value":head.value(final).squeeze(-1),
                "allocation_scores":head.allocation(final).squeeze(-1),"cash_scores":head.cash(final.mean(1)),
                "shared_latent":final,"router_probabilities":gates,
                "policy_validity":market_mask[...,:0],"coverage":market_mask.any(-1)}
        policy_mask=torch.stack([validity[k] for k in self.policy_ids],-1)
        tokens=torch.stack([self.policy_adapters[k](evidence[k]) for k in self.policy_ids],-2)
        policy_gates=None
        if self.stock_policy_ids:
            policy_logits=torch.cat([self.policy_router[k](evidence[k]) for k in self.policy_ids],-1)
            policy_logits=policy_logits/max(.05,float(routing.get("policy",{}).get("temperature",1)))
            policy_k=int(routing.get("policy",{}).get("top_k",0))
            if 0<policy_k<len(self.policy_ids):
                selected=torch.zeros_like(policy_mask).scatter_(-1,policy_logits.masked_fill(~policy_mask,-1e9).topk(policy_k,-1).indices,True)
                policy_mask=policy_mask&selected
            policy_gates=policy_logits.masked_fill(~policy_mask,-1e9).softmax(-1)*policy_mask
            policy_gates=policy_gates/policy_gates.sum(-1,keepdim=True).clamp_min(1e-9)
            tokens=tokens*policy_gates[...,None]*policy_mask.sum(-1)[...,None,None]
        b,n,e,w=tokens.shape
        unavailable=~policy_mask.any(-1)
        safe_mask=~policy_mask.clone();safe_mask[unavailable,0]=False
        tokens=tokens.masked_fill(unavailable[...,None,None],0)
        policy,_=self.policy_attention(latent.reshape(b*n,1,w),tokens.reshape(b*n,e,w),tokens.reshape(b*n,e,w),
            key_padding_mask=safe_mask.reshape(b*n,e))
        policy=policy.reshape(b,n,w).masked_fill(unavailable[...,None],0)
        final=self.controller_norm(latent+policy+self.account_context(account))
        head=self.market_fusion
        prior=torch.zeros_like(head.policy(final));allocation_prior=torch.zeros_like(head.allocation(final).squeeze(-1))
        if policy_q is not None:
            if self.stock_policy_ids:
                stock_mask=policy_mask
                stock_votes=torch.stack([policy_q[k][...,:3] for k in self.stock_policy_ids],-2)
                stock_gates=policy_gates*stock_mask
                stock_gates=stock_gates/stock_gates.sum(-1,keepdim=True).clamp_min(1e-9)
                probabilities=(stock_votes*stock_gates[...,None]).sum(-2)
                stock_prior=probabilities.clamp_min(1e-6).log()
                stock_targets=torch.stack([policy_q[k][...,3] for k in self.stock_policy_ids],-1)
                target=(stock_targets*stock_gates).sum(-1).clamp(1e-6,1-1e-6)
                active=stock_mask.any(-1)
                prior=torch.where(active[...,None],stock_prior,prior)
                allocation_prior=torch.where(active,torch.logit(target),allocation_prior)
        return {"policy_logits":head.policy(final)+prior,"value":head.value(final).squeeze(-1),
            "allocation_scores":head.allocation(final).squeeze(-1)+allocation_prior,"cash_scores":head.cash(final.mean(1)),
            "shared_latent":final,"router_probabilities":gates,"policy_validity":policy_mask,
            "coverage":market_mask.any(-1)|policy_mask.any(-1),
            **({"policy_router_probabilities":policy_gates} if policy_gates is not None else {})}
