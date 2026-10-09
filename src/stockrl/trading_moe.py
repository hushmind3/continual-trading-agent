"""Reusable trainable evidence adapters and frozen Expert evidence input calibration."""
import torch
from torch import nn


class EvidenceAdapter(nn.Module):
    def __init__(self,size):
        super().__init__()
        self.scale=nn.Parameter(torch.ones(size))
        self.bias=nn.Parameter(torch.zeros(size))
    def forward(self,values):
        return values*self.scale+self.bias
