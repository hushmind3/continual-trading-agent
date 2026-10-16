"""Portable source packages, independent of this platform or a user's model."""
import hashlib
import json
import os
from pathlib import Path
import uuid
import zipfile
from . import adapters, installer, runtime, store

KINDS = {'static', 'vite', 'fastapi', 'python-cli', 'node-mcp'}
MAX_EXPANDED = 128 * 1024 * 1024
MAX_ARCHIVE = 32 * 1024 * 1024
SKIP = {'.git', '.venv', 'venv', 'node_modules', '.platform-runtime', '__pycache__',
        '.pytest_cache', '.mypy_cache', '.cache', '.runtime', 'runtime', 'logs', 'data'}


def export(key):
    with store.LOCK, runtime.LOCK:
        record = store.read(key)
        if installer.JOBS or runtime.busy_reason() or installer.RESTARTING:
            raise ValueError('설치·실행이 끝난 뒤 내보내세요.')
        source = Path(record.get('active_source') or '').resolve()
        base = store.owned(store.STATE, 'projects/' + store.identifier(key))
        if not source.is_relative_to(base.resolve()) or not source.is_dir(): raise ValueError('내보낼 설치 소스가 없습니다.')
        spec = adapters.validate(source, record['adapter'])
        if spec['kind'] not in KINDS:
            raise ValueError('공용 플랫폼에 의존하는 모듈은 아직 독립 실행 패키지로 내보낼 수 없습니다.')
        target = base / 'exports'; target.mkdir(exist_ok=True)
        archive_name = key + '-' + uuid.uuid4().hex[:12] + '.zip'
        path = target / archive_name
        metadata = {'schema': 1, 'id': key, 'title': record.get('title', key), 'url': record['url'],
                    'adapter': spec, 'environment_keys': sorted(record.get('environment', {})), 'files': {}}
        total = 0
        try:
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
                for root, directories, files in os.walk(source, followlinks=False):
                    directories[:] = [name for name in directories if name not in SKIP and not name.endswith('.egg-info')]
                    for name in directories:
                        if (Path(root) / name).is_symlink() or getattr(os.path, 'isjunction', lambda value: False)(Path(root) / name):
                            raise ValueError('연결 폴더는 독립 패키지에 넣을 수 없습니다.')
                    for name in files:
                        file = Path(root) / name
                        if name == '.env' or name.startswith('.env.') and not name.endswith(('.example', '.sample', '.template')): continue
                        if name in ('config.json', 'credentials.json', 'secrets.json') or file.suffix in ('.pyc', '.log', '.sqlite', '.db'): continue
                        if file.is_symlink(): raise ValueError('연결 파일은 독립 패키지에 넣을 수 없습니다.')
                        total += file.stat().st_size
                        if total > MAX_EXPANDED: raise ValueError('앱 소스가 내보내기 한도 128 MiB를 넘습니다.')
                        relative = file.relative_to(source).as_posix()
                        if relative == 'platform-project.json': continue
                        data = file.read_bytes()
                        metadata['files']['source/' + relative] = hashlib.sha256(data).hexdigest()
                        archive.writestr('source/' + relative, data)
                descriptor = json.dumps(spec, ensure_ascii=False).encode('utf8')
                archive.writestr('source/platform-project.json', descriptor)
                metadata['files']['source/platform-project.json'] = hashlib.sha256(descriptor).hexdigest()
                archive.writestr('app-package.json', json.dumps(metadata, ensure_ascii=False, indent=2))
                archive.write(Path(__file__).with_name('portable_runner.py'), 'run.py')
                archive.write(Path(__file__).with_name('portable_web.py'), '_platform_web.py')
                archive.writestr('README.md', instructions(metadata))
            if path.stat().st_size > MAX_ARCHIVE: raise ValueError('압축 파일이 가져오기 한도 32 MiB를 넘습니다.')
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return {'id': key, 'filename': archive_name, 'bytes': path.stat().st_size,
                'url': '/assets/project-packages/' + key + '/' + archive_name,
                'independent': True, 'includes_data': False}


def instructions(metadata):
    return f'''# {metadata['title']} 독립 실행 안내

용도: 플랫폼 없이 원본 앱을 실행하거나 플랫폼에 다시 설치하는 소스 패키지입니다.
원본: {metadata['url']}

- Python 3.11 이상과 원본이 요구하는 Node.js 등 실행기를 준비합니다.
- 압축을 푼 폴더에서 `python run.py setup`으로 의존성을 설치합니다.
- `python run.py check`로 진입점을 확인하고 `python run.py run`으로 실행합니다.
- 웹앱 기본 주소는 http://127.0.0.1:8080 이며 `--port`로 바꿀 수 있습니다.
- MCP 앱은 원본 stdio 서버로 실행합니다. `python run.py mcp-config`로 다른 에이전트에 넣을 설정을 출력합니다.
- 플랫폼의 프로젝트 관리 → 앱 파일에서 설치로 이 ZIP을 선택하면 다시 연결합니다.

환경 변수 이름: {', '.join(metadata['environment_keys']) or '지정된 값 없음'}
환경 변수 값·로그·DB·학습 모델·사용 데이터·config.json·.env는 포함하지 않습니다. 필요한 값은 새 환경에서 설정하세요.
웹 UI가 있는 FastAPI 앱은 API와 UI를 같은 독립 실행기에 연결합니다.
MCP 서버 자체에 없는 채팅 UI나 모델을 새로 포함하지 않습니다. 원본의 라이선스와 사용 조건을 따릅니다.
다른 PC의 의존성 설치·원본 외부 서비스 연결까지 성공했다는 검증 기록은 아닙니다.
'''
