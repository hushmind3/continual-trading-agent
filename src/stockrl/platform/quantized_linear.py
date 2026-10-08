"""Portable weight-only INT8/INT4: packed residency, bounded floating-point execution.

Activations remain floating point. This is not an accelerated integer GEMM kernel;
the comparison lab measures whether the memory saving merits its decode cost.
"""
import math
import torch
from torch import nn
from torch.nn import functional as F


def pack_weight(weight, bits, group_size=64,device='cpu'):
    if bits not in (4,8) or weight.ndim!=2:raise ValueError('INT4/INT8 Linear 가중치가 필요합니다.')
    rows,columns=weight.shape;groups=math.ceil(columns/group_size);width=groups*group_size
    packed=torch.empty((rows,width//2 if bits==4 else width),dtype=torch.uint8 if bits==4 else torch.int8)
    scales=torch.empty((rows,groups),dtype=torch.float32)
    maximum=7 if bits==4 else 127
    for start in range(0,rows,128):
        value=weight[start:start+128].detach().to(device=device,dtype=torch.float32)
        if not torch.isfinite(value).all():raise ValueError('유효하지 않은 가중치는 변환할 수 없습니다.')
        value=F.pad(value,(0,width-columns)).reshape(-1,groups,group_size)
        scale=value.abs().amax(-1).clamp_min(torch.finfo(torch.float32).tiny)/maximum
        q=(value/scale.unsqueeze(-1)).round().clamp(-maximum,maximum).to(torch.int8).reshape(-1,width)
        if bits==4:
            q=(q.to(torch.int16)+8).to(torch.uint8)
            q=q[:,0::2]|(q[:,1::2]<<4)
        packed[start:start+128]=q.cpu();scales[start:start+128]=scale.cpu()
    return packed,scales


class PackedLinear(nn.Module):
    def __init__(self, original, bits, group_size=64):
        super().__init__();self.in_features=original.in_features;self.out_features=original.out_features
        self.bits=bits;self.group_size=group_size
        width=math.ceil(self.in_features/group_size)*group_size
        device=original.weight.device
        self.register_buffer('qweight',torch.empty((self.out_features,width//2 if bits==4 else width),device=device,dtype=torch.uint8 if bits==4 else torch.int8))
        self.register_buffer('scales',torch.empty((self.out_features,width//group_size),device=device,dtype=torch.float32))
        self.register_parameter('bias',original.bias)

    def decode(self,start=0,end=None,dtype=torch.float32):
        q=self.qweight[start:end]
        if self.bits==4:
            q=torch.stack((q&15,q>>4),-1).flatten(-2).to(torch.int8)-8
        groups=self.scales.shape[-1]
        return (q.to(dtype).reshape(-1,groups,self.group_size)*self.scales[start:end].to(dtype).unsqueeze(-1)).flatten(1)[:,:self.in_features]

    @property
    def weight(self):
        # Compatibility for architectures that inspect a Linear's dtype/device.
        return self.decode()

    def forward(self, inputs):
        # Cap each reconstructed matrix at 16 MiB, rather than unpacking a whole Expert.
        block=max(1,min(self.out_features,(16*2**20)//max(self.in_features*inputs.element_size(),1)))
        output=inputs.new_empty((*inputs.shape[:-1],self.out_features))
        for start in range(0,self.out_features,block):
            end=min(start+block,self.out_features)
            bias=self.bias[start:end].to(inputs.dtype) if self.bias is not None else None
            output[...,start:end]=F.linear(inputs,self.decode(start,end,inputs.dtype),bias)
        return output


def linear_layers(expert):
    """Only ordinary untied Linear weights; embeddings/custom/functional attention stay native."""
    storage={}
    for name,param in expert.named_parameters(remove_duplicate=False):
        storage.setdefault((param.untyped_storage().data_ptr(),param.storage_offset()),[]).append(name)
    result={}
    for name,module in expert.named_modules():
        if type(module) is not nn.Linear:continue
        parent=expert.get_submodule(name.rsplit('.',1)[0]) if '.' in name else expert
        if isinstance(parent,nn.MultiheadAttention):continue
        if len(storage[(module.weight.untyped_storage().data_ptr(),module.weight.storage_offset())])>1:continue
        result[name]=module
    return result


def restore_packed(model,state,layers,prefix=''):
    for name,spec in layers.items():
        if prefix and not name.startswith(prefix+'.'):continue
        local=name.removeprefix(prefix+'.') if prefix else name
        original=model.get_submodule(local)
        if type(original) is not nn.Linear:raise ValueError('변환 패키지의 Linear 구조가 원본과 다릅니다: '+local)
        parent,_,child=local.rpartition('.')
        model.get_submodule(parent)._modules[child]=PackedLinear(original,spec['bits'],spec['group_size'])
    return model.load_state_dict(state,strict=True,assign=True)
