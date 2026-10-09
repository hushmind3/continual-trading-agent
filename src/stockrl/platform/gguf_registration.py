"""Store original GGUF bytes once; register a small JSON input/executor manifest."""
import json
import re
import shutil
from .expert_packages import digest,PACKAGE_FORMAT,package_path
from .expert_contracts import descriptor
from ..state_io import atomic_json


def inspect_gguf(path):
    with path.open('rb') as stream:
        if stream.read(4)!=b'GGUF':raise ValueError('GGUF 파일 magic이 다릅니다.')
    return dict(id=re.sub('[^a-z0-9_]','_',path.stem.lower())[:64],name=path.stem,
        input=dict(supported=True,pipeline='gguf_market',requires=['완료 가격 시계열','llama.cpp 로컬 구조화 의견'],minimum_history=32,universe=None))


def register_gguf(settings,path,slot,progress,origin=None):
    inspect_gguf(path);model=settings.resolve(settings.expert_checkpoint);root=model.parent/'expert-packages';root.mkdir(exist_ok=True)
    from .gguf_format import quantize_if_needed
    path,kind=quantize_if_needed(settings,path,progress)
    progress(stage='gguf_register',detail='GGUF 원본 checksum과 로컬 입력 계약 확인')
    checksum=digest(path);target=root/(checksum[:24]+'.gguf')
    if target.exists():
        if digest(target)!=checksum:raise ValueError('보관된 동일 이름의 GGUF가 손상됐습니다.')
    elif path.parent.name.startswith('.download-') or path.parent.name=='incoming':path.replace(target)
    elif path.resolve().is_relative_to(model.parent.resolve()):target=path
    else:shutil.copyfile(path,target)
    weight=dict(file=target.relative_to(model.parent).as_posix(),sha256=checksum,bytes=target.stat().st_size)
    package=dict(format=PACKAGE_FORMAT,id=slot,executor='llama_cpp',module_count=1,feature_size=6,state_dict={},metadata={},
        representation=f'GGUF · quantized type {kind}',weight_asset=weight,
        entry=dict(id=slot,name=origin['repository'] if origin else path.stem,backend='gguf_market',frozen=True,weight_bytes=weight['bytes'],dtype='GGUF',origin=origin))
    manifest=root/(slot+'.json');atomic_json(package,manifest);reference=dict(file=manifest.relative_to(model.parent).as_posix(),sha256=digest(manifest),bytes=manifest.stat().st_size)
    item=descriptor(slot,package,reference);item['weight_bytes']=weight['bytes'];return item
