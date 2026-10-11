"""Frozen NF4 buffers executed by bitsandbytes' native 4-bit kernels."""
import torch
from torch import nn


def pack_nf4(weight,device='cuda:0'):
    import bitsandbytes.functional as F
    value=weight.detach().to(device=device,dtype=torch.bfloat16)
    if not torch.isfinite(value).all():raise ValueError('NF4 원본 가중치에 유효하지 않은 값이 있습니다.')
    packed,state=F.quantize_4bit(value,quant_type='nf4',compress_statistics=True)
    return {'qweight':packed.cpu(),**{'qs_'+k.replace('.','_'):v.cpu() for k,v in state.as_dict(packed=True).items()}}


class NF4Linear(nn.Module):
    def __init__(self,original,state):
        super().__init__();self.in_features=original.in_features;self.out_features=original.out_features
        self.register_parameter('bias',original.bias)
        for key,value in state.items():self.register_buffer(key,value)

    def quant_state(self):
        from bitsandbytes.functional import QuantState
        values={k.removeprefix('qs_').replace('quant_state_bitsandbytes__','quant_state.bitsandbytes__'):v for k,v in self._buffers.items() if k.startswith('qs_')}
        return QuantState.from_dict(values,device=self.qweight.device)

    @property
    def weight(self):
        # Some native architectures inspect Linear.weight. Never cache a float copy.
        from bitsandbytes.functional import dequantize_4bit
        return dequantize_4bit(self.qweight,self.quant_state())

    def forward(self,inputs):
        import bitsandbytes as bnb
        dtype=inputs.dtype
        value=inputs.to(torch.bfloat16)
        bias=self.bias.to(value.dtype) if self.bias is not None else None
        return bnb.matmul_4bit(value,self.qweight.t(),quant_state=self.quant_state(),bias=bias).to(dtype)


def replace_nf4(original,state):
    return NF4Linear(original,{k:v for k,v in state.items() if k=='qweight' or k.startswith('qs_')})
