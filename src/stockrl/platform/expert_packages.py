"""Immutable per-Expert assets; the learned MoE header stays small and replaceable."""
from __future__ import annotations

import gc
import hashlib
from pathlib import Path
import torch

from .model_composition import atomic_torch_save

HEADER_FORMAT='registered_vertical_trading_moe_v2'
PACKAGE_FORMAT='frozen_expert_package_v1'


def digest(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()


def package_path(header_path, reference):
    root=Path(header_path).resolve().parent
    path=(root/reference['file']).resolve()
    if not path.is_relative_to(root):raise ValueError('Expert 패키지는 모델 폴더 안에 있어야 합니다.')
    if not path.is_file() or path.stat().st_size!=reference['bytes']:
        raise ValueError('Expert 패키지가 없거나 크기가 달라졌습니다: '+path.name)
    return path


def split_asset(path, progress=lambda **kw:None):
    """One migration writes each frozen tensor once; future edits change only the header."""
    path=Path(path);saved=torch.load(path,map_location='cpu',weights_only=True,mmap=True)
    # The small mutable header must not remain mmap-locked during online learning on Windows.
    if saved.get('format')==HEADER_FORMAT:return torch.load(path,map_location='cpu',weights_only=True)
    if saved.get('format')!='registered_vertical_trading_moe_v1':raise ValueError('지원하는 MoE 파일이 아닙니다.')
    destination=path.parent/'expert-packages';destination.mkdir(exist_ok=True)
    references={};ids=list(saved['expert_mapping'])
    for index,key in enumerate(ids):
        entry=saved['expert_mapping'][key];prefix=f'experts.{key}.'
        weights={name.removeprefix(prefix):value for name,value in saved['state_dict'].items() if name.startswith(prefix)}
        if not weights:raise ValueError('Expert 가중치 누락: '+key)
        progress(stage='packaging',expert=key,completed=index,total=len(ids))
        package=dict(format=PACKAGE_FORMAT,id=key,entry=entry,state_dict=weights,
                     module_count=saved['config']['native_module_counts'][key],
                     feature_size=saved['config']['feature_sizes'][key],
                     metadata=dict(architecture_sources=saved['metadata']['architecture_sources'],
                         native_runner_source=saved['metadata']['native_runner_source'],
                         construction_input=saved['metadata']['construction_inputs'].get(key)))
        partial=atomic_torch_save(package,destination/(key+'.pt'))
        checked=torch.load(partial,map_location='cpu',weights_only=True,mmap=True)
        for name,value in checked['state_dict'].items():
            expected=weights[name].reshape(-1);actual=value.reshape(-1)
            for start in range(0,actual.numel(),262144):
                if not torch.equal(actual[start:start+262144],expected[start:start+262144]):
                    raise ValueError('패키지 가중치가 원본과 다릅니다: '+key+'/'+name)
        del checked,expected,actual,value
        revision=digest(partial);target=destination/(key+'-'+revision[:16]+'.pt')
        # Complete artifacts are immutable. Failed migrations can reuse a verified artifact.
        if target.exists():
            if digest(target)!=revision:raise ValueError('동일 이름의 패키지가 손상됐습니다.')
            partial.unlink()
        else:partial.replace(target)
        references[key]=dict(file=target.relative_to(path.parent).as_posix(),sha256=revision,bytes=target.stat().st_size)
        del weights,package
    result={**saved,'format':HEADER_FORMAT,'expert_packages':references,
            'state_dict':{k:v.clone() for k,v in saved['state_dict'].items() if not k.startswith('experts.')}}
    partial=atomic_torch_save(result,path)
    verify=torch.load(partial,map_location='cpu',weights_only=True)
    if set(verify['expert_packages'])!=set(ids):raise ValueError('패키지 목록이 일치하지 않습니다.')
    for key,reference in references.items():package_path(path,reference)
    del result,saved,verify;gc.collect();partial.replace(path)
    progress(stage='complete',completed=len(ids),total=len(ids))
    return torch.load(path,map_location='cpu',weights_only=True)


def load_package(header_path,reference,verify=False):
    path=package_path(header_path,reference)
    if verify and digest(path)!=reference['sha256']:raise ValueError('Expert 패키지 checksum이 다릅니다.')
    saved=torch.load(path,map_location='cpu',weights_only=True,mmap=True)
    if saved.get('format')!=PACKAGE_FORMAT:raise ValueError('Frozen Expert 패키지 형식이 아닙니다.')
    return saved
