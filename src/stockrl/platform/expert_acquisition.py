"""Download a discovered revision, match its input template and register one frozen package."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import zipfile
from .expert_discovery import candidate,slot_name
from .expert_packages import load_package,digest
from .native_upgrade import read_native,match_weights
from .library_store import fetch_source,register_package


def acquire(settings,catalog,payload,progress):
    selected=candidate(catalog,payload);key=selected.get('template');template=catalog['experts'].get(key)
    for item in catalog['experts'].values():
        try:origin=load_package(settings.resolve(settings.expert_checkpoint),item['package'])['entry'].get('origin') or {}
        except (OSError,ValueError):continue
        if origin.get('repository')==selected['repository'] and origin.get('revision')==selected['revision']:
            raise ValueError('이 원본 revision은 이미 라이브러리에 보관되어 있습니다. 중복 다운로드하지 않았습니다.')
    root=settings.resolve(settings.expert_checkpoint).parent/'expert-packages';root.mkdir(exist_ok=True)
    total=selected['bytes']
    if shutil.disk_usage(root).free<total*2+settings.resources.disk_reserve_gib*2**30:raise ValueError('다운로드와 패키지 생성에 필요한 디스크 공간이 부족합니다.')
    weights={};provenance=[]
    with tempfile.TemporaryDirectory(prefix='.download-',dir=root) as temporary:
        for index,file in enumerate(selected['files']):
            progress(stage='acquiring',detail=f"원본 {index+1}/{len(selected['files'])} 다운로드 · {selected['repository']}")
            path=fetch_source(settings,file['url'],progress,root=Path(temporary))
            checksum=digest(path)
            if file.get('sha256') and checksum!=file['sha256']:raise ValueError('다운로드 파일 checksum이 원본과 다릅니다.')
            values=read_native(path)
            if len(selected['files'])==1:weights=values
            else:
                if set(weights).intersection(values):raise ValueError('checkpoint shard에 중복 tensor가 있습니다.')
                weights.update(values)
            provenance.append(dict(name=file['name'],sha256=checksum,bytes=path.stat().st_size))
        if selected.get('executor')=='hf_forecast':
            from .hf_forecast import construct
            from .expert_packages import PACKAGE_FORMAT
            import torch
            # Metadata only: actual bytes are restored from the downloaded tensors below.
            with torch.device('meta'):model=construct(selected['model_config'],selected['backend'])
            definitions=io.BytesIO()
            with zipfile.ZipFile(definitions,'w'):pass
            package=dict(format=PACKAGE_FORMAT,executor='hf_forecast',module_count=1,feature_size=12,
                state_dict={'models.0.'+k:v for k,v in model.state_dict().items()},
                entry=dict(backend=selected['backend'],parameters=selected['parameters'],frozen=True),
                metadata=dict(architecture_sources=definitions.getvalue(),native_runner_source='',model_config=selected['model_config']))
        else:package=load_package(settings.resolve(settings.expert_checkpoint),template['package'],verify=True)
        matched=match_weights(weights,package)
        if matched is None:raise ValueError('다운로드한 실제 tensor가 검증된 입력 템플릿과 일치하지 않습니다. 구성에 추가하지 않았습니다.')
        fingerprint=hashlib.sha256(json.dumps(provenance,sort_keys=True).encode()).hexdigest()
        package={**package,'state_dict':matched,'entry':{**package['entry'],'name':selected['repository'],
            'checkpoint_sha256':fingerprint,'weight_bytes':sum(v.numel()*v.element_size() for v in matched.values()),
            'origin':dict(repository=selected['repository'],revision=selected['revision'],files=provenance)},
            'metadata':{**package['metadata'],**({'input_template_sha256':template['package']['sha256']} if template else {})}}
        return register_package(settings,package,slot_name(selected,catalog),progress),key
