"""Admission/lab device choice from available VRAM and measured peak use."""
import psutil
import torch


def choose_device(settings,requested='auto',weight_bytes=0,peak_vram=0,conversion=False):
    if requested not in ('auto','cpu','cuda:0'):raise ValueError('auto / cpu / cuda:0 중에서 선택하세요.')
    available=psutil.virtual_memory().available
    decision=dict(device='cpu',reason='CPU 선택',ram_available_bytes=available)
    if requested=='cpu':return decision
    if torch.cuda.is_available():
        free,total=torch.cuda.mem_get_info()
        from .resources import ResourceMonitor
        system_gpu=ResourceMonitor(settings.state_dir).snapshot({})['gpu']
        if system_gpu.get('total_bytes'):
            free=min(free,max(0,system_gpu['total_bytes']-system_gpu['used_bytes']))
            decision['gpu_utilization_percent']=system_gpu.get('utilization_percent')
        # Conversion transfers a bounded tensor/chunk, not an entire model.
        required=max(peak_vram*1.1,64*2**20 if conversion else weight_bytes*1.35)
        reserve=settings.resources.vram_reserve_gib*2**30
        decision.update(vram_free_bytes=free,vram_total_bytes=total,vram_required_bytes=int(required),vram_reserve_bytes=int(reserve))
        if free>=required+reserve:
            return {**decision,'device':'cuda:0','reason':'가용 VRAM에 모델·연산 여유가 있어 CUDA 선택'}
        decision['reason']='현재 GPU 사용량과 VRAM 여유 기준으로 CPU 선택'
    else:decision['reason']='CUDA 장치를 사용할 수 없어 CPU 선택'
    if requested=='cuda:0':raise MemoryError(decision['reason'])
    return decision
