"""Merge only shared-browser settings; leave models, credentials and other profiles intact."""
import json
import os
from pathlib import Path
import re
import shutil
import threading
import tomllib
from platform_modules import ROOT
from . import browser, state

LOCK = threading.RLock()
CLI = Path(__file__).with_name('cli.py')
PYTHON = ROOT / '.venv/platform' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
CODEX = ROOT / '.codex/config.toml'
HERMES = ROOT / 'runtime/ai_agent/HermesOriginal/home'
OPENCLAW = ROOT / 'runtime/ai_agent/OpenClawOriginal/home/openclaw.json'


def _command(mode):
    return {'command': str(PYTHON), 'args': [str(CLI), mode]}


def status():
    record = state.STATE / 'agents.json'
    try:
        return json.loads(record.read_text())
    except (OSError, ValueError):
        return {'configured': False, 'message': '에이전트 공용 연결 설정 전'}


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.shared-tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(text)
    os.replace(temporary, path)


def connect():
    with LOCK, state.exclusive('agent-settings'):
        current = browser.start()
        endpoint = current['endpoint']
        # Parse everything before changing existing installation settings.
        original = CODEX.read_text() if CODEX.exists() else ''
        parsed = tomllib.loads(original)
        config = json.loads(OPENCLAW.read_text()) if OPENCLAW.exists() else None
        if config is not None and not isinstance(config.get('browser', {}), dict):
            raise ValueError('OpenClaw browser 설정 형식을 확인하세요.')
        if config is not None and not isinstance(config.get('browser', {}).get('profiles', {}), dict):
            raise ValueError('OpenClaw browser.profiles 설정 형식을 확인하세요.')
        profiles = [HERMES, *sorted((HERMES / 'profiles').glob('*'))] if HERMES.exists() else []
        profile_texts = [(home, (home / '.env').read_text() if (home / '.env').exists() else '')
                         for home in profiles if home.is_dir()]
        section = '\n# BEGIN platform-shared-accounts\n'
        for name, mode in [('platform_accounts', 'mcp-accounts'), ('platform_browser', 'mcp-browser')]:
            command = _command(mode)
            existing = parsed.get('mcp_servers', {}).get(name)
            if existing and '# BEGIN platform-shared-accounts' not in original:
                raise ValueError(f'기존 {name} MCP 설정이 있어 덮어쓰지 않았습니다.')
            section += f'\n[mcp_servers.{name}]\ncommand = {json.dumps(command["command"], ensure_ascii=False)}\nargs = {json.dumps(command["args"], ensure_ascii=False)}\n'
        section += '# END platform-shared-accounts\n'
        updated = re.sub(r'\n?# BEGIN platform-shared-accounts\n.*?# END platform-shared-accounts\n?', '', original, flags=re.S)
        tomllib.loads(updated + section)
        # Snapshot only the files being changed, inside the owning runtime folder.
        backup = state.private_directory() / 'settings-before-shared'
        backup.mkdir(exist_ok=True, mode=0o700)
        if CODEX.exists() and not (backup / 'codex-config.toml').exists():
            shutil.copy2(CODEX, backup / 'codex-config.toml')
        _write(CODEX, updated.rstrip() + '\n' + section)
        configured = []
        for home, text in profile_texts:
            path = home / '.env'
            destination = backup / ('hermes-' + ('base' if home == HERMES else home.name) + '.env')
            if path.exists() and not destination.exists():
                shutil.copy2(path, destination)
                os.chmod(destination, 0o600)
            text = re.sub(r'(?m)^(?:export\s+)?BROWSER_CDP_URL=.*\n?', '', text)
            _write(path, text.rstrip() + f'\nBROWSER_CDP_URL={endpoint}\n')
            skill = home / 'skills/shared-accounts/SKILL.md'
            instruction = (f'---\nname: shared-accounts\ndescription: 공용 계정 및 가입 진행표와 로그인된 공용 브라우저 사용\n---\n'
                           f'공용 계정 작업은 `{PYTHON} "{CLI}" list`로 업체 목록을 먼저 확인한다. '
                           '브라우저 도구는 BROWSER_CDP_URL의 공용 전용 브라우저를 사용한다. '
                           '같은 업체를 동시에 가입하지 않는다. 대기 중인 업체를 선택해 working으로 기록하고 실제 결과에 따라 갱신한다. '
                           '추가 인증·CAPTCHA·필요한 약관 동의는 waiting_user로 기록하고 사용자에게 넘긴다. 확인 없이 가입 완료로 표시하지 않는다. '
                           '비밀번호·쿠키·API 키를 메모·대화·파일에 복사하지 않는다. '
                           f'키 저장은 공용 설정 화면, 키 사용은 `{PYTHON} "{CLI}" run --service ID --env ENV_NAME -- COMMAND`로 환경변수 주입한다. '
                           f'업체 상태 갱신은 `{PYTHON} "{CLI}" update ID STATUS --notes "결과"`를 사용한다.\n')
            _write(skill, instruction)
            configured.append('base' if home == HERMES else home.name)
        if config is not None:
            if not (backup / 'openclaw.json').exists():
                shutil.copy2(OPENCLAW, backup / 'openclaw.json')
                os.chmod(backup / 'openclaw.json', 0o600)
            settings = config.setdefault('browser', {})
            settings.setdefault('profiles', {})['platform'] = {'cdpUrl': endpoint, 'attachOnly': True}
            settings['enabled'] = True
            settings['defaultProfile'] = 'platform'
            _write(OPENCLAW, json.dumps(config, ensure_ascii=False, indent=2) + '\n')
            _write(OPENCLAW.parent / 'skills/shared-accounts/SKILL.md',
                   f'---\nname: shared-accounts\ndescription: 공용 로그인 브라우저와 업체 가입 진행표 사용\n---\n'
                   f'브라우저 작업은 platform 프로필을 사용한다. 공용 업체 목록은 `{PYTHON} "{CLI}" list`로 확인한다. '
                   f'실제 진행 결과는 `{PYTHON} "{CLI}" update ID STATUS --notes "결과"`로 기록한다. '
                   'working은 한 담당자만 사용하고, 추가 인증·CAPTCHA·필요한 약관 동의는 waiting_user로 기록해 사용자에게 넘긴다. '
                   '키·쿠키·비밀번호를 메모나 결과에 남기지 않는다. '
                   f'API 키는 공용 설정에서 보관하고 `{PYTHON} "{CLI}" run --service ID --env API_KEY -- COMMAND`로 실행 시 주입한다.\n')
        result = {'configured': True, 'endpoint': endpoint, 'hermes_profiles': configured,
                  'openclaw': config is not None, 'codex': True, 'updated_at': state.now(),
                  'message': '설정 저장 완료 · Codex 도구는 다음 연결부터, Hermes는 새 대화부터 사용. 실행 검증은 별도입니다.'}
        state.write_json(state.STATE / 'agents.json', result)
        return result
