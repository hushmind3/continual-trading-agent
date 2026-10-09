"""Allocation-only financial controller using pinned Qwen attention, SwiGLU and RMSNorm."""
from types import SimpleNamespace
import torch
from torch import nn
from .qwen_layers import Qwen3_5Attention,Qwen3_5MLP,Qwen3_5RMSNorm

DEFAULT_NETWORK=dict(hidden_size=512,num_attention_heads=8,num_key_value_heads=4,
    head_dim=64,intermediate_size=1792,rms_norm_eps=1e-6,attention_dropout=0.,
    attention_bias=False,hidden_act='silu',asset_chunk=32)


class ExpertAttention(nn.Module):
    def __init__(self,settings):
        super().__init__();self.settings=settings
        cfg=SimpleNamespace(**settings,_attn_implementation='sdpa')
        self.input_norm=Qwen3_5RMSNorm(cfg.hidden_size,cfg.rms_norm_eps)
        self.attention=Qwen3_5Attention(cfg,0)
        self.ffn_norm=Qwen3_5RMSNorm(cfg.hidden_size,cfg.rms_norm_eps)
        self.ffn=Qwen3_5MLP(cfg,cfg.intermediate_size)
        for module in (self.attention,self.ffn):
            for layer in module.modules():
                if isinstance(layer,nn.Linear):
                    nn.init.normal_(layer.weight,std=.02)
                    if layer.bias is not None:nn.init.zeros_(layer.bias)

    def forward(self,query,tokens,valid):
        shape=query.shape;query=query.reshape(-1,shape[-1]);tokens=tokens.reshape(len(query),-1,shape[-1]);valid=valid.reshape(len(query),-1)
        result=[]
        for offset in range(0,len(query),self.settings['asset_chunk']):
            q=query[offset:offset+self.settings['asset_chunk']];k=tokens[offset:offset+len(q)]
            values=torch.cat([k,q[:,None]],1)
            keep=torch.cat([valid[offset:offset+len(q)],torch.ones((len(q),1),dtype=torch.bool,device=q.device)],-1)
            mask=torch.zeros((len(q),1,1,values.shape[1]),device=q.device,dtype=q.dtype).masked_fill(~keep[:,None,None],float('-inf'))
            # Expert slots are an unordered set: identity RoPE avoids inventing temporal positions.
            cos=values.new_ones((len(q),values.shape[1],self.settings['head_dim']));sin=torch.zeros_like(cos)
            attended,_=self.attention(self.input_norm(values),(cos,sin),mask)
            hidden=q+attended[:,-1]
            result.append(hidden+self.ffn(self.ffn_norm(hidden)))
        return torch.cat(result,0).reshape(shape)


class PortfolioController(nn.Module):
    def __init__(self,sizes,stock_policy_ids=(),network=None):
        super().__init__();self.settings={**DEFAULT_NETWORK,**(network or {})};width=self.settings['hidden_size']
        self.policy_ids=list(stock_policy_ids);self.market_ids=sorted(k for k in sizes if k not in self.policy_ids)
        self.router=nn.ModuleDict({k:nn.Linear(sizes[k],1) for k in self.market_ids})
        self.context_routers=nn.ModuleDict({k:nn.Linear(16,1) for k in self.market_ids})
        self.projections=nn.ModuleDict({k:nn.Linear(sizes[k],width) for k in self.market_ids})
        self.market_projection=nn.Linear(16,width);self.market_context=nn.Linear(8,width)
        self.market_block=ExpertAttention(self.settings)
        self.policy_adapters=nn.ModuleDict({k:nn.Linear(sizes[k]+4,width) for k in self.policy_ids})
        self.policy_router=nn.ModuleDict({k:nn.Linear(sizes[k],1) for k in self.policy_ids})
        self.policy_block=ExpertAttention(self.settings)
        self.output_norm=Qwen3_5RMSNorm(width,self.settings['rms_norm_eps'])
        self.allocation=nn.Linear(width,1);self.cash=nn.Linear(width,1)
        self.target_prior_gain=nn.Parameter(torch.tensor(1.))
        nn.init.normal_(self.allocation.weight,std=.02);nn.init.zeros_(self.allocation.bias)
        nn.init.normal_(self.cash.weight,std=.02);nn.init.zeros_(self.cash.bias)

    @staticmethod
    def gates(logits,mask):
        weights=logits.masked_fill(~mask,-1e9).softmax(-1)*mask
        return weights/weights.sum(-1,keepdim=True).clamp_min(1e-9)

    def forward(self,evidence,validity,account,market,policy_q):
        query=self.market_projection(account)+self.market_context(market)
        if self.market_ids:
            mask=torch.stack([validity[k] for k in self.market_ids],-1)
            logits=torch.cat([self.router[k](evidence[k])+self.context_routers[k](account) for k in self.market_ids],-1)
            gates=self.gates(logits,mask)
            tokens=torch.stack([self.projections[k](evidence[k]) for k in self.market_ids],-2)
            tokens=tokens*gates[...,None]*mask.sum(-1)[...,None,None]
        else:
            tokens=query.new_zeros((*query.shape[:-1],0,query.shape[-1]));mask=torch.zeros((*query.shape[:-1],0),dtype=torch.bool,device=query.device)
        latent=self.market_block(query,tokens,mask)
        prior=latent.new_zeros(latent.shape[:-1]);coverage=mask.any(-1)
        if self.policy_ids:
            pmask=torch.stack([validity[k] for k in self.policy_ids],-1)
            pgates=self.gates(torch.cat([self.policy_router[k](evidence[k]) for k in self.policy_ids],-1),pmask)
            ptokens=torch.stack([self.policy_adapters[k](torch.cat([evidence[k],policy_q[k]],-1)) for k in self.policy_ids],-2)
            ptokens=ptokens*pgates[...,None]*pmask.sum(-1)[...,None,None]
            latent=self.policy_block(latent,ptokens,pmask)
            # Opinions are inputs, not forced orders; their influence is trainable.
            targets=torch.stack([policy_q[k][...,3] for k in self.policy_ids],-1)
            prior=(targets*pgates).sum(-1)*self.target_prior_gain
            coverage=coverage|pmask.any(-1)
        latent=self.output_norm(latent)
        return dict(shared_latent=latent,allocation_scores=self.allocation(latent).squeeze(-1)+prior,
            cash_scores=self.cash(latent.mean(-2)),coverage=coverage,target_prior=prior)
