"""Same-architecture native weight updates use a proven input/definition template."""
import io
import zipfile
import torch
from .expert_packages import load_package,digest


def read_native(path):
    if path.suffix.lower()=='.safetensors':
        from safetensors.torch import load_file
        return load_file(path,device='cpu')
    if path.suffix.lower()=='.zip':
        with zipfile.ZipFile(path) as archive:
            if 'policy.pth' not in archive.namelist():raise ValueError('SB3 policy.pth가 없는 ZIP입니다.')
            return torch.load(io.BytesIO(archive.read('policy.pth')),map_location='cpu',weights_only=True)
    try:return torch.load(path,map_location='cpu',weights_only=True,mmap=True)
    except RuntimeError:return torch.load(path,map_location='cpu',weights_only=True)


def match_weights(saved,package):
    if package['module_count']!=1:return None
    expected={k.removeprefix('models.0.'):v for k,v in package['state_dict'].items()}
    candidates=[saved,*[saved.get(k) for k in ('state_dict','model_state_dict','model','policy')]] if isinstance(saved,dict) else []
    for values in candidates:
        if not isinstance(values,dict) or not values or not all(torch.is_tensor(v) for v in values.values()):continue
        for prefix in ('','module.','_orig_mod.'):
            candidate={k.removeprefix(prefix):v for k,v in values.items()}
            if set(candidate)==set(expected) and all(candidate[k].shape==expected[k].shape for k in expected):
                return {'models.0.'+k:v for k,v in candidate.items()}
    return None


def inspect_native(settings,path,catalog):
    raw=read_native(path);matches=[]
    for key,item in catalog.get('experts',{}).items():
        if not item['input']['supported']:continue
        package=load_package(settings.resolve(settings.expert_checkpoint),item['package'])
        if match_weights(raw,package) is not None:
            matches.append(dict(id=key,name=item['name']+' · 동일 구조 가중치',input=item['input'],native_template=True))
    if not matches:raise ValueError('검증된 입력 템플릿과 일치하는 가중치 구조가 없습니다. 원본 구조·입력 계약을 포함한 Expert 패키지가 필요합니다.')
    return matches


def upgrade_from_template(settings,path,item):
    package=load_package(settings.resolve(settings.expert_checkpoint),item['package'],verify=True)
    weights=match_weights(read_native(path),package)
    if weights is None:raise ValueError('선택한 입력 템플릿과 가중치의 이름·크기가 일치하지 않습니다.')
    return {**package,'state_dict':weights,'entry':{**package['entry'],'checkpoint_sha256':digest(path),
            'checkpoint_bytes':path.stat().st_size},'metadata':{**package['metadata'],'input_template_sha256':item['package']['sha256']}}
