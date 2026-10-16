"""Validate portable archives and reuse the normal install/verify transaction."""
import base64
import binascii
import hashlib
import io
import json
import os
from pathlib import PurePosixPath
import re
import shutil
import uuid
import zipfile
from . import adapters, installer, packages, store
from .github import repository


def install(encoded):
    if not isinstance(encoded, str) or len(encoded) > (packages.MAX_ARCHIVE * 4 // 3 + 8):
        raise ValueError('앱 압축 파일은 32 MiB 이하만 설치할 수 있습니다.')
    try: data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc: raise ValueError('올바른 앱 압축 파일이 아닙니다.') from exc
    stage = store.STATE / 'imports' / uuid.uuid4().hex
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            files = archive.infolist()
            if len(files) > 20000 or sum(file.file_size for file in files) > packages.MAX_EXPANDED:
                raise ValueError('압축을 푼 앱 소스가 허용 크기를 넘습니다.')
            names = set()
            for file in files:
                path = PurePosixPath(file.filename)
                if (path.is_absolute() or '..' in path.parts or '\\' in file.filename or ':' in file.filename
                    or path.as_posix() != file.filename.rstrip('/')
                    or any(part.rstrip('. ') != part or re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part) for part in path.parts)
                    or file.filename.casefold() in names or (file.external_attr >> 16) & 0o170000 == 0o120000):
                    raise ValueError('안전하지 않은 앱 파일 경로입니다.')
                names.add(file.filename.casefold())
            if 'app-package.json' not in archive.namelist(): raise ValueError('앱 내보내기로 만든 ZIP을 선택하세요.')
            metadata = json.loads(archive.read('app-package.json'))
            if metadata.get('schema') != 1 or metadata.get('adapter', {}).get('kind') not in packages.KINDS:
                raise ValueError('지원하지 않는 앱 패키지 규격입니다.')
            repo = repository(metadata.get('url', ''))
            digests = metadata.get('files')
            if not isinstance(digests, dict) or not digests: raise ValueError('앱 파일 검증 정보가 없습니다.')
            actual = {file.filename for file in files if file.filename.startswith('source/') and not file.is_dir()}
            if actual != set(digests): raise ValueError('앱 파일 목록이 패키지 정보와 다릅니다.')
            for name, digest in digests.items():
                content = archive.read(name)
                if hashlib.sha256(content).hexdigest() != digest: raise ValueError('패키지의 파일 검증에 실패했습니다.')
                relative = PurePosixPath(name)
                if any(part in packages.SKIP for part in relative.parts): raise ValueError('실행 환경·사용 데이터는 앱 소스에 넣을 수 없습니다.')
                target = store.owned(stage, name)
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)
            source = stage / 'source'
            spec = adapters.validate(source, metadata['adapter'])
            (source / 'platform-project.json').write_text(json.dumps(spec, ensure_ascii=False), encoding='utf8')
        with store.LOCK:
            result = installer.start('https://github.com/' + repo, source, False, False, cleanup_import=True)
        stage = None  # The installer owns staging cleanup after copying (also on failure/cancellation).
        return result
    except (zipfile.BadZipFile, KeyError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('앱 압축 파일이 손상됐거나 규격에 맞지 않습니다.') from exc
    finally:
        if stage and stage.exists(): shutil.rmtree(stage)
