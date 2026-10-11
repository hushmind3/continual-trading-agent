"""Pinned official llama.cpp GPU binary; no Python rebuild or floating-point weights."""
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import zipfile
import requests
from ..state_io import read_json,atomic_json


def ensure_engine(settings,progress=lambda **kw:None):
    root=settings.state_dir/'engines'/'llama.cpp';manifest=read_json(root/'engine.json')
    if manifest and (root/'llama-server.exe').is_file() and (root/'llama-quantize.exe').is_file():return root/'llama-server.exe'
    response=requests.get('https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=5');response.raise_for_status()
    release=next((r for r in response.json() if any(a['name'].endswith('bin-win-vulkan-x64.zip') for a in r['assets'])),None)
    if not release:raise ValueError('공식 Windows GPU llama.cpp 실행 파일을 찾지 못했습니다.')
    asset=next(a for a in release['assets'] if a['name'].endswith('bin-win-vulkan-x64.zip'))
    # Vulkan executes compressed kernels on NVIDIA GPUs without another CUDA toolkit copy.
    root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.llama-',dir=root.parent) as directory:
        path=Path(directory)/'engine.zip';digest=hashlib.sha256();size=0
        with requests.get(asset['browser_download_url'],stream=True) as download:
            download.raise_for_status()
            with path.open('wb') as stream:
                for chunk in download.iter_content(1024*1024):
                    digest.update(chunk);stream.write(chunk);size+=len(chunk)
                    progress(stage='engine_download',completed=size,total=asset['size'],detail='공식 llama.cpp GPU 실행기 다운로드')
        if size!=asset['size']:raise ValueError('llama.cpp 실행기 다운로드 크기가 다릅니다.')
        if asset.get('digest') and asset['digest']!='sha256:'+digest.hexdigest():raise ValueError('llama.cpp 공개 checksum과 다릅니다.')
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                name=Path(member.filename).name
                if name in ('llama-server.exe','llama-quantize.exe') or name.endswith('.dll'):
                    with archive.open(member) as source,(root/name).open('wb') as target:shutil.copyfileobj(source,target)
        atomic_json(dict(release=release['tag_name'],source=asset['browser_download_url'],sha256=digest.hexdigest(),backend='Vulkan GPU / CPU hybrid'),root/'engine.json')
    if not (root/'llama-server.exe').is_file():raise ValueError('다운로드에 llama-server가 없습니다.')
    return root/'llama-server.exe'
