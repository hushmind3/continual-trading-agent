"""Candidate discovery and immutable package registration; no portfolio effects."""
import re
import time
from pathlib import Path
import requests
import torch
from ..state_io import read_json,atomic_json
from .expert_packages import HEADER_FORMAT,PACKAGE_FORMAT,digest,load_package
from .expert_contracts import descriptor,input_contract
from .model_composition import atomic_torch_save


def catalog_path(settings):return settings.state_dir/'expert-library.json'


def save_catalog(settings,header,catalog=None):
    path=catalog_path(settings);catalog=catalog or read_json(path) or dict(experts={})
    for key,reference in header['expert_packages'].items():
        package=load_package(settings.resolve(settings.expert_checkpoint),reference)
        value=descriptor(key,package,reference)
        previous=catalog['experts'].get(key,{})
        if previous.get('package',{}).get('sha256')==reference['sha256']:
            value['check']=previous.get('check',value['check'])
            if value.get('conversion'):value['conversion']=previous.get('conversion',value['conversion'])
        catalog['experts'][key]=value
    catalog.update(active=catalog.get('active',header.get('active_experts',sorted(header['expert_mapping']))),
                   installed={k:r['sha256'] for k,r in header['expert_packages'].items()},updated=time.time())
    atomic_json(catalog,path);return catalog


def fetch_source(settings,source,progress,root=None):
    if not source:raise ValueError('Expert 패키지 파일 경로나 다운로드 주소를 입력하세요.')
    if not str(source).startswith(('http://','https://')):
        path=Path(source).expanduser().resolve()
        if not path.is_file():raise ValueError('파일이 없습니다.')
        return path
    root=Path(root) if root is not None else settings.resolve(settings.expert_checkpoint).parent/'expert-packages'/'incoming';root.mkdir(parents=True,exist_ok=True)
    partial=root/'download.partial'
    try:
        with requests.get(source,stream=True,timeout=(10,30)) as response:
            response.raise_for_status();total=int(response.headers.get('Content-Length',0));size=0
            import shutil
            if total and shutil.disk_usage(root).free-total<settings.resources.disk_reserve_gib*2**30:
                raise ValueError('다운로드할 디스크 여유 공간이 부족합니다.')
            with partial.open('wb') as stream:
                for block in response.iter_content(1024*1024):
                    stream.write(block);size+=len(block)
                    if shutil.disk_usage(root).free<settings.resources.disk_reserve_gib*2**30:raise ValueError('디스크 여유 공간 부족')
                    progress(stage='downloading',completed=size,total=total,detail='패키지 다운로드 중')
        from urllib.parse import urlsplit
        suffix=Path(urlsplit(source).path).suffix.lower()
        target=root/(digest(partial)+(suffix if suffix in ('.pt','.pth','.zip','.safetensors','.gguf') else '.pt'));partial.replace(target);return target
    except BaseException:
        partial.unlink(missing_ok=True);raise


def inspect_source(path,settings=None,catalog=None):
    if path.suffix.lower()=='.gguf':
        from .gguf_registration import inspect_gguf
        return [inspect_gguf(path)]
    from .native_upgrade import read_native,inspect_native
    saved=read_native(path)
    if saved.get('format')==PACKAGE_FORMAT:
        entries={saved['id']:saved['entry']}
    elif saved.get('format') in ('registered_vertical_trading_moe_v1',HEADER_FORMAT):entries=saved['expert_mapping']
    else:
        if settings is not None:return inspect_native(settings,path,catalog)
        raise ValueError('입력 템플릿 또는 Expert 패키지가 필요합니다.')
    return [dict(id=key,name=entry.get('name',key),input=input_contract(entry)) for key,entry in entries.items()]


def import_package(settings,path,key,slot,progress,template=None):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,79}',slot):raise ValueError('슬롯 이름은 영문 소문자·숫자·밑줄로 지정하세요.')
    if slot in dir(torch.nn.ModuleDict()):raise ValueError('모델 내부에서 사용하는 이름입니다. 다른 슬롯 이름을 지정하세요.')
    if path.suffix.lower()=='.gguf':
        from .gguf_registration import register_gguf
        return register_gguf(settings,path,slot,progress)
    from .native_upgrade import read_native,upgrade_from_template
    saved=read_native(path)
    if saved.get('format')==PACKAGE_FORMAT:
        package=saved;key=saved['id']
    elif saved.get('format')==HEADER_FORMAT:
        if key not in saved['expert_mapping']:raise ValueError('이 파일에 해당 Expert가 없습니다.')
        package=saved.get('frozen_experts',{}).get(key) or load_package(path,saved['expert_packages'][key],verify=True)
        if package.get('embedded_weight') is not None:
            # A GGUF export is registered with its native file using the existing importer.
            from .integrated_asset import materialize_gguf
            from .gguf_registration import register_gguf
            return register_gguf(settings,materialize_gguf(settings,key,package),slot,progress)
    elif saved.get('format')=='registered_vertical_trading_moe_v1':
        if key not in saved['expert_mapping']:raise ValueError('추가할 Expert를 선택하세요.')
        package=dict(format=PACKAGE_FORMAT,id=key,entry=saved['expert_mapping'][key],
            state_dict={name.removeprefix(f'experts.{key}.'):v for name,v in saved['state_dict'].items() if name.startswith(f'experts.{key}.')},
            module_count=saved['config']['native_module_counts'][key],feature_size=saved['config']['feature_sizes'][key],
            metadata=dict(architecture_sources=saved['metadata']['architecture_sources'],
                native_runner_source=saved['metadata']['native_runner_source'],construction_input=saved['metadata']['construction_inputs'].get(key)))
    elif template:package=upgrade_from_template(settings,path,template)
    else:raise ValueError('지원하지 않는 패키지 형식')
    return register_package(settings,package,slot,progress)


def register_package(settings,package,slot,progress):
    contract=input_contract(package['entry'])
    if not contract['supported']:raise ValueError(contract['reason'])
    if not 3<package['feature_size']<=32768:raise ValueError('출력 크기가 지원 범위를 벗어났습니다.')
    package={**package,'id':slot,'entry':{**package['entry'],'id':slot}}
    root=settings.resolve(settings.expert_checkpoint).parent/'expert-packages';root.mkdir(parents=True,exist_ok=True)
    progress(stage='importing',detail='Frozen 패키지를 등록하는 중')
    temporary=atomic_torch_save(package,root/(slot+'.pt'))
    checksum=digest(temporary);target=root/(slot+'-'+checksum[:16]+'.pt')
    if target.exists():
        if digest(target)!=checksum:raise ValueError('기존 패키지가 손상됐습니다. 삭제 후 다시 가져오세요.')
        temporary.unlink()
    else:temporary.replace(target)
    reference=dict(file=target.relative_to(root.parent).as_posix(),sha256=checksum,bytes=target.stat().st_size)
    return descriptor(slot,package,reference)
