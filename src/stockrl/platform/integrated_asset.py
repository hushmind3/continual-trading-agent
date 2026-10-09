"""Champion contains selected frozen low-bit bodies and the learned central state."""
import shutil
from pathlib import Path
import torch
from .expert_packages import load_package,package_path,digest


def read_header(path):
    saved=torch.load(path,map_location='cpu',weights_only=True,mmap=True)
    saved.pop('frozen_experts',None)
    # Mutable head tensors must not keep the large source mmap locked on Windows.
    def clone(value):
        if torch.is_tensor(value):return value.clone()
        if isinstance(value,dict):return {k:clone(v) for k,v in value.items()}
        if isinstance(value,list):return [clone(v) for v in value]
        return value
    return clone(saved)


def integrate(header,path,active,progress=lambda **kw:None):
    path=Path(path);bodies={};params=0;weight_bytes=0
    for index,key in enumerate(active):
        progress(stage='integrating',completed=index,total=len(active),detail=f'Champion에 양자화 Expert 통합 · {key}')
        package=dict(load_package(path,header['expert_packages'][key],verify=True))
        if package.get('executor')=='llama_cpp':
            weight=package_path(path,package['weight_asset'])
            if not package['entry'].get('parameters'):
                from .gguf_format import describe
                package['entry']={**package['entry'],'parameters':describe(weight)['parameters']}
            package['embedded_weight']=torch.from_file(str(weight),shared=False,size=weight.stat().st_size,dtype=torch.uint8)
            weight_bytes+=weight.stat().st_size
        else:weight_bytes+=sum(v.numel()*v.element_size() for v in package['state_dict'].values())
        bodies[key]=package;params+=int(package['entry'].get('parameters',0))
    if shutil.disk_usage(path.parent).free<weight_bytes+2**30:raise OSError('통합 Champion을 원자적으로 저장할 디스크 여유가 부족합니다.')
    header.update(frozen_experts=bodies,integrated_experts=True,
        integrated_summary=dict(expert_ids=list(active),frozen_parameters=params,frozen_weight_bytes=weight_bytes))
    return header


def materialize_gguf(settings,key,package):
    """llama.cpp needs a native file: extract only its declared embedded bytes."""
    reference=package['weight_asset'];root=settings.state_dir/'engines';root.mkdir(exist_ok=True)
    path=root/(key+'-'+reference['sha256'][:16]+'.gguf')
    if not path.is_file() or path.stat().st_size!=reference['bytes'] or digest(path)!=reference['sha256']:
        temporary=path.with_suffix('.partial');data=package['embedded_weight']
        try:
            with temporary.open('wb') as stream:
                for offset in range(0,data.numel(),8*2**20):stream.write(data[offset:offset+8*2**20].numpy().tobytes())
                stream.flush()
                import os
                os.fsync(stream.fileno())
            if digest(temporary)!=reference['sha256']:raise ValueError('Champion 내부 GGUF 가중치가 손상됐습니다.')
            temporary.replace(path)
        finally:temporary.unlink(missing_ok=True)
    return path
