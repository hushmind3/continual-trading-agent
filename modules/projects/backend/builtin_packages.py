"""Export one built-in module with its own copy of the host/UI source template."""
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
import zipfile
from . import store

SUPPORTED = {'finance', 'rea', 'hermes'}
TEMPLATE = ('package.json', 'package-lock.json', 'frontend', 'backend',
            'development/scripts/install_windows.py', 'development/scripts/module_sources.py',
            'development/scripts/start_server.py', 'development/scripts/server_watchdog.py',
            'development/scripts/requirements/platform.txt')


def source_files(root, key):
    # Include new program files too, while respecting private/runtime gitignore
    # rules. Read working copies rather than reverting user changes to HEAD.
    result = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z', '--', *TEMPLATE, 'modules/' + key,
                             'LICENSE', 'LICENSE.md', 'LICENSE.txt'], cwd=root,
                            check=True, capture_output=True)
    for name in result.stdout.decode('utf8').split('\0'):
        if not name: continue
        relative = Path(name)
        if '/configs/local/' in '/' + relative.as_posix(): continue
        if relative.name == '.env' or relative.name.startswith('.env.') and not relative.name.endswith(('.example', '.sample', '.template')): continue
        if relative.parts[0] == 'backend' and len(relative.parts) != 2: continue
        if relative.parts[0] == 'frontend' and any(part in {'tests', 'test-results', 'dist'} for part in relative.parts): continue
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('연결 파일은 독립 실행 소스에 포함할 수 없습니다: ' + name)
        yield name, path


def export(key):
    from platform_modules import ROOT
    if key not in SUPPORTED: raise ValueError('독립 실행 내보내기를 지원하지 않는 기본 모듈입니다.')
    folder = ROOT / 'modules' / key
    metadata = json.loads((folder / 'module.json').read_text(encoding='utf8'))
    if metadata['id'] != key: raise ValueError('모듈 등록 ID가 폴더와 다릅니다.')
    target = store.owned(store.STATE, 'projects/' + key + '/exports')
    target.mkdir(parents=True, exist_ok=True)
    name = key + '-' + uuid.uuid4().hex[:12] + '.zip'
    path = target / name
    manifest = {'schema': 1, 'kind': 'standalone-module', 'module': key,
                'title': metadata['group']['title'], 'includes_data': False, 'files': {}}
    documentation = {
        'backend/README.md': f'# 독립 API 호스트\n\n용도: `{key}`의 단일 /api와 전용 실행 프로세스를 연결하는 이 배포본의 호스트 복사본입니다. 업무 코드는 [선택 모듈](../modules/{key}/README.md), 설치·실행은 [상위 안내](../README.md)를 따릅니다. 원래 플랫폼 폴더나 다른 업무 모듈을 import하지 않습니다.\n',
        'frontend/README.md': f'# 독립 화면\n\n용도: `{key}` 화면과 React/Vite/Tailwind 렌더러의 복사본입니다. 공통 UI는 src/ui, 테마는 src/tailwind.css, 실제 화면은 [선택 모듈](../modules/{key}/frontend/README.md)에 있습니다. 루트에서 npm ci, npm run build --workspace frontend로 빌드합니다. 설치·서버 실행은 [상위 안내](../README.md)를 따릅니다.\n',
        'frontend/src/pages/README.md': f'# 화면 위치\n\n용도: 이 배포본의 실제 화면은 [선택 모듈](../../../modules/{key}/frontend/README.md)에 있습니다. 다른 업무 모듈은 포함하지 않습니다.\n',
        f'modules/{key}/README.md': f'# {key} 독립 모듈\n\n용도: backend·frontend·module.json·의존성 명세를 자체 소유하는 선택 모듈입니다. 이 배포본의 API/UI 복사본에 자동 등록합니다. [백엔드](backend/README.md)·[프론트엔드](frontend/README.md)를 따라 구현을 수정할 수 있습니다.\n\n설치·검사·실행은 [상위 안내](../../README.md)의 setup/check/run을 따릅니다. 전용 Python 패키지는 .venv에 설치하며 설정·데이터·모델은 새 환경에서 준비합니다. 원래 프로젝트를 찾거나 다른 업무 모듈의 코드·설정을 사용하지 않습니다.\n',
    }
    engine = ROOT / 'runtime/shared/engines/llama.cpp/engine.json'
    if key == 'hermes' and engine.is_file():
        receipt = json.loads(engine.read_text(encoding='utf8'))
        if all(field in receipt for field in ('release','source','sha256')):
            manifest['llama_cpp'] = {field:receipt[field] for field in ('release','source','sha256')}
    try:
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            total = 0
            for relative, file in source_files(ROOT, key):
                data = documentation[relative].encode('utf8') if relative in documentation else file.read_bytes()
                total += len(data)
                if total > 512 * 1024 * 1024: raise ValueError('독립 실행 소스가 512 MiB 한도를 넘습니다.')
                archive.writestr(relative, data)
                manifest['files'][relative] = hashlib.sha256(data).hexdigest()
            runner = Path(__file__).with_name('standalone_runner.py').read_bytes()
            archive.writestr('run.py', runner)
            manifest['files']['run.py'] = hashlib.sha256(runner).hexdigest()
            archive.writestr('standalone-module.json', json.dumps(manifest, ensure_ascii=False, indent=2))
            archive.writestr('modules/README.md', f'# 독립 모듈\n\n용도: 이 배포본은 `{key}` 하나와 실행에 필요한 호스트/UI 복사본을 소유합니다. 설정·실행은 [상위 안내](../README.md)를 따릅니다. 원래 플랫폼과 다른 모듈은 필요하지 않습니다.\n')
            archive.writestr('README.md', instructions(key))
            archive.writestr('설치.cmd', '@echo off\r\ncd /d "%~dp0"\r\npy run.py setup\r\npause\r\n')
            archive.writestr('실행.cmd', '@echo off\r\ncd /d "%~dp0"\r\npy run.py run\r\npause\r\n')
            for action,title in (('setup','설치'),('check','검사'),('run','실행')):
                entry=zipfile.ZipInfo(title+'.command');entry.create_system=3;entry.external_attr=(0o100755 << 16)
                archive.writestr(entry, '#!/bin/zsh\nset -e\ncd "${0:A:h}"\nexport PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"\npython3 run.py '+action+'\n')
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {'id': key, 'filename': name, 'bytes': path.stat().st_size,
            'url': '/assets/project-packages/' + key + '/' + name,
            'independent': True, 'includes_data': False, 'kind': 'standalone-module'}


def instructions(key):
    return f'''# {key} 독립 실행 소스

용도: 이 폴더만 별도 위치로 옮겨 사용하는 Windows 소스 배포본입니다. 원래 플랫폼 폴더·다른 업무 모듈·Codex는 실행 의존성이 아닙니다.

- 필요한 공통 API·React/Vite/Tailwind UI 소스의 복사본과 modules/{key}만 들어 있습니다.
- 설치된 Python·Node/npm·Git이 필요합니다. Hermes는 기존 설치 경로에 따라 Python 3.14와 uv도 사용합니다. 외부 실행기는 설치 전 준비해야 합니다.
- `설치.cmd`(Windows) / `설치.command`(Mac) 또는 `python run.py setup`: 이 폴더 안의 전용 환경에 의존성을 설치하고 화면을 빌드합니다. 원래 플랫폼 환경을 수정하지 않습니다.
- `python run.py check`: 파일 무결성·단독 모듈 로딩·설치/빌드 여부를 확인합니다.
- `실행.cmd`(Windows) / `실행.command`(Mac) 또는 `python run.py run --port 8080`: 단일 API와 원래 UI를 실행합니다.
- 설정·DB·대화·모델·키는 자동 포함하지 않습니다. 새 설정은 이 폴더의 configs/runtime 또는 해당 모듈의 configs에 생성합니다. 필요한 원본 모델·외부 서비스는 별도로 지정하세요.
- Hermes는 내보낸 공개 버전 정보가 있으면 Windows setup은 공개 배포 정보가 있으면 SHA-256을 검사하고 Mac setup은 설치된 Homebrew Metal 실행기를 사용해 이 폴더의 runtime/shared/engines/llama.cpp에 설치합니다. 컴퓨터 조작 드라이버도 setup이 설치하며 모델 원본은 다운로드하지 않습니다. 다른 모델 서버 주소를 연결할 수도 있습니다.
- 다른 PC의 GPU 드라이버·거래 인증·모든 분석 도구를 포함한 실행까지 보증하는 설치 파일은 아닙니다.
- 이 ZIP은 기본 모듈의 독립 소스 배포본입니다. GitHub 외부 앱 ZIP 가져오기와 형식이 다릅니다. 다시 조립하려면 modules/{key}를 호환 플랫폼의 modules에 넣고 전용 환경을 설치합니다.
'''
