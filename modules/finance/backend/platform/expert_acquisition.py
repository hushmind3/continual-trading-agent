"""Download original repositories without creating weight packages or executing models."""
import json
from pathlib import Path
import shutil
import zipfile


def download_source(settings,catalog,payload,progress):
    """Download public source files without inspecting weights or registering an executor."""
    import re,requests
    from ..state_io import atomic_json
    selected=next((row for row in catalog.get('discovery',{}).get('models',[]) if row['id']==payload.get('id')),None)
    if not selected:raise ValueError('검색 결과에서 다운로드할 항목을 선택하세요.')
    repository=selected['repository'];revision=selected.get('revision')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository) or not revision:raise ValueError('저장소 경로·버전 정보가 부족합니다.')
    requested_revision=revision
    if selected.get('source')=='GitHub':
        commit=requests.get('https://api.github.com/repos/'+repository+'/commits/'+revision,timeout=(5,15))
        commit.raise_for_status();revision=commit.json()['sha']
    role=selected.get('role') if selected.get('role') in ('market','action') else 'market'
    root=settings.model_dir.resolve();destination=root/role/repository.split('/')[-1]
    if not destination.resolve().is_relative_to(root):raise ValueError('다운로드 경로가 모델 폴더 밖에 있습니다.')
    metadata=destination/'download.json'
    if metadata.exists():
        saved=json.loads(metadata.read_text(encoding='utf8'))
        if saved.get('repository')==repository and saved.get('revision')==revision:return {**saved,'existing':True}
        raise ValueError('이 모델 폴더에 다른 버전이 있습니다. 기존 원본을 덮어쓰지 않습니다.')
    destination.mkdir(parents=True,exist_ok=True)
    progress(stage='downloading',detail='원본 저장 경로: '+str(destination))
    if selected.get('source')=='GitHub':
        archive=destination/'source.zip'
        if archive.exists():raise ValueError('기존 source.zip을 덮어쓰지 않습니다.')
        url='https://codeload.github.com/'+repository+'/zip/'+revision
        with requests.get(url,stream=True,timeout=(10,60)) as response:
            response.raise_for_status()
            with archive.open('xb') as stream:
                for block in response.iter_content(1024*1024):
                    if progress(stage='downloading',detail='저장소 원본 다운로드: '+str(destination)) is False:raise InterruptedError('다운로드 중지')
                    stream.write(block)
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                parts=Path(member.filename).parts[1:]
                if not parts or member.is_dir():continue
                target=destination.joinpath(*parts).resolve()
                if not target.is_relative_to(destination.resolve()):raise ValueError('원본 압축 파일에 잘못된 경로가 있습니다.')
                if target.exists():raise ValueError('기존 모델 파일과 원본 압축 경로가 겹칩니다: '+target.name)
                target.parent.mkdir(parents=True,exist_ok=True)
                with source.open(member) as original,target.open('xb') as output:shutil.copyfileobj(original,output)
        kind='source_repository'
    else:
        from huggingface_hub import snapshot_download,HfApi
        names=HfApi(token=False).list_repo_files(repository,revision=revision)
        collisions=[name for name in names if (destination/name).exists()]
        if collisions:raise ValueError('기존 원본 파일을 덮어쓰지 않습니다: '+', '.join(collisions[:3]))
        snapshot_download(repo_id=repository,revision=revision,local_dir=str(destination),token=False,max_workers=2)
        kind='model_repository'
    result={'repository':repository,'revision':revision,'requested_revision':requested_revision,'destination':str(destination),'source':selected.get('source'),
        'kind':kind,'registered':False,'requires_fit':selected.get('requires_fit',False),'runtime_status':'입력·실행기 연결은 별도','documentation':selected.get('input_evidence',{})}
    atomic_json(result,metadata)
    return result

