"""One shared GPU budget, LRU RAM offload and Accelerate layer dispatch."""
import torch
import psutil
import time
from ..state_io import read_json
from ..expert_device import restore_host
from .resources import ResourceMonitor


class Residency:
    def __init__(self,pool):self.pool=pool;self.monitor=ResourceMonitor(pool.settings.state_dir);self.pinned=set()

    def free(self):
        free,total=torch.cuda.mem_get_info();gpu=self.monitor.snapshot({})['gpu']
        if gpu.get('total_bytes'):free=min(free,max(0,gpu['total_bytes']-gpu['used_bytes']))
        return free,total

    def offload(self,key):
        expert=self.pool.loaded[key]
        amount=sum(p.numel()*p.element_size() for p in list(expert.parameters())+list(expert.buffers()) if p.is_cuda)
        if hasattr(expert,'details'):amount=expert.details.get('resident_bytes') or 0
        if getattr(expert,'_layer_offloaded',False):return 0
        restore_host(expert)
        if hasattr(expert,'offload'):expert.offload()
        self.pool.metrics.setdefault(key,{}).update(residency='ram_offload',resident_bytes=0)
        torch.cuda.empty_cache();return amount

    def device(self,key,expert,peak):
        settings=self.pool.settings;preference=settings.resources.expert_devices.get(key,'auto')
        if preference=='cpu' or not torch.cuda.is_available():return 'cpu'
        if getattr(expert,'_layer_offloaded',False):return 'cuda:0'
        free,total=self.free()
        tensors=list(expert.parameters())+list(expert.buffers())
        weights=sum(p.numel()*p.element_size() for p in tensors)
        if hasattr(expert,'reference'):
            # llama.cpp decides how many layers fit on Vulkan; remaining layers stay RAM-backed.
            return 'cuda:0'
        resident=any(p.is_cuda for p in tensors) or hasattr(expert,'child') and expert.child is not None and expert.device!='cpu'
        workspace=self.pool.metrics.get(key,{}).get('peak_workspace_bytes',0)
        required=workspace+(0 if resident else weights)
        for other in list(self.pool.loaded):
            if free>=required:break
            if other!=key and other not in self.pinned:free+=self.offload(other)
        if free>=required:return 'cuda:0'
        # An oversized model streams only its overflow layers from RAM to GPU.
        gpu_budget=max(0,int(free-workspace))
        if self.pool.keep_device and weights>gpu_budget and not hasattr(expert,'reference'):
            from accelerate import dispatch_model,infer_auto_device_map
            restore_host(expert)
            budget=gpu_budget;ram=max(0,int(psutil.virtual_memory().available))
            classes=sorted({type(m).__name__ for m in expert.modules() if any(x in type(m).__name__ for x in ('Block','DecoderLayer','Attention'))})
            mapping=infer_auto_device_map(expert,max_memory={0:budget,'cpu':ram},no_split_module_classes=classes)
            if any(v=='disk' for v in mapping.values()):raise MemoryError('GPU와 RAM의 운영 여유 공간에 모델이 들어가지 않습니다.')
            if any(v==0 or str(v).startswith('cuda') for v in mapping.values()) and any(v=='cpu' for v in mapping.values()):
                dispatch_model(expert,device_map=mapping,offload_buffers=True)
                expert._layer_offloaded=True;self.pool.metrics.setdefault(key,{}).update(residency='gpu_ram_layer_offload',device_map={k:str(v) for k,v in mapping.items()})
                return 'cuda:0'
        if preference=='cuda:0':raise MemoryError('CUDA 실행의 모델·연산 여유 공간이 부족합니다.')
        restore_host(expert);return 'cpu'

    def preload(self,keys,progress=lambda **kw:None,stopped=lambda:False):
        from ..expert_device import host_state,finish_device
        keys=list(keys)
        for index,key in enumerate(keys):
            if stopped():break
            progress(key=key,completed=index,total=len(keys))
            try:
                expert=self.pool.get(key);device=self.device(key,expert,0)
                if hasattr(expert,'start'):expert.start(device)
                elif device.startswith('cuda') and not getattr(expert,'_layer_offloaded',False):
                    home=host_state(expert);expert.to(device);finish_device(expert,home,device)
                if device.startswith('cuda') and not getattr(expert,'_layer_offloaded',False):self.pinned.add(key)
                self.pool.metrics.setdefault(key,{}).update(device=device,residency='gpu_ram_layer_offload' if getattr(expert,'_layer_offloaded',False) else 'gpu_resident' if device!='cpu' else 'ram_offload',
                    resident_bytes=sum(p.numel()*p.element_size() for p in list(expert.parameters())+list(expert.buffers()) if p.is_cuda),preloaded=True)
                if hasattr(expert,'details'):
                    layers=expert.details.get('gpu_layers')
                    self.pool.metrics[key].update(**expert.details,device=('gpu' if layers else 'cpu') if layers is not None else device,
                        residency=('gpu_resident' if layers==expert.details.get('total_layers') else 'gpu_cpu_hybrid' if layers else 'ram_offload') if layers is not None else 'device_unconfirmed')
                rss=self.pool.process.memory_info().rss
                if getattr(expert,'child',None):rss+=psutil.Process(expert.child.pid).memory_info().rss
                self.pool.metrics[key]['rss_bytes']=rss
            except Exception as exc:self.pool.metrics.setdefault(key,{}).update(status='waiting_resources',error=str(exc),preloaded=False)
