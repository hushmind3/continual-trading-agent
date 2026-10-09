"""One GPU owner with shared market views and bounded in-memory Expert evidence."""
import threading
import torch
import pandas as pd
from ..market_reader import IncrementalMarketCSV
from .environment import market_view


class MoESession:
    def __init__(self, settings):
        self.settings=settings
        self.device=torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        self.closing=threading.Event()
        self.market_lock=threading.RLock();self.evidence_lock=threading.Lock()
        self.reader=IncrementalMarketCSV(settings.state_dir/'live'/'market.csv',retain_timestamps=256)
        self.signature=None;self.frame=None;self.view=None;self.view_signature=None
        self.packets={};self.failures={}
        self.market_builds=0;self.view_builds=0

    def stopped(self, role):
        return self.closing.is_set() or (self.settings.state_dir/'workers'/'agent.stop').exists()

    def market(self, *, view=False):
        with self.market_lock:
            if not self.reader.path.exists():return None,None,None
            frame,signature=self.reader.refresh()
            if frame is None or frame.empty:return None,None,signature
            if signature!=self.signature:
                self.frame=frame.copy()
                self.frame['date']=pd.to_datetime(self.frame.date,utc=True).dt.tz_localize(None)
                self.signature=signature;self.market_builds+=1
                self.reader.processed_through=str(self.frame.date.max())
            if view and signature!=self.view_signature:
                self.view,self.frame=market_view(self.frame)
                self.view_signature=signature;self.view_builds+=1
            return self.view if view else None,self.frame,signature

    def put_evidence(self, key, packets):
        with self.evidence_lock:self.packets[key]=packets

    def evidence(self, active):
        with self.evidence_lock:
            # Removing a slot also releases its cached GPU output, not just its weights.
            self.packets={k:v for k,v in self.packets.items() if k in active}
            return self.packets.copy()

    def metadata(self, actor,critic=None):
        from .policy import parameters
        params=parameters(actor,critic or actor)
        summary=actor.model_spec.get('integrated_summary') or {}
        return dict(execution='unified-gpu-moe-v1',execution_device=str(self.device),
            hidden_size=actor.model_spec['config'].get('central',{}).get('hidden_size',512),
            attention_heads=actor.model_spec['config'].get('central',{}).get('num_attention_heads',8),
            ffn_size=actor.model_spec['config'].get('central',{}).get('intermediate_size',1792),
            central_parameters=sum(p.numel() for p in params),trainable_parameters=sum(p.numel() for p in params if p.requires_grad),
            central_weight_bytes=sum(p.numel()*p.element_size() for p in params),
            frozen_parameters=summary.get('frozen_parameters'),frozen_weight_bytes=summary.get('frozen_weight_bytes'),
            integrated_expert_ids=summary.get('expert_ids'),
            market_builds=self.market_builds,market_view_builds=self.view_builds,
            shared_expert_evidence=True)


def optimizer_to(optimizer, device):
    """Adam moments follow their parameters; non-capturable scalar step stays on CPU."""
    for state in optimizer.state.values():
        for key,value in state.items():
            if torch.is_tensor(value) and key!='step':state[key]=value.to(device)
