"""Set the password used by the browser-only remote dashboard login."""
from __future__ import annotations

import getpass
import json
import os
import secrets
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'runtime/platform/remote_access.json'


def main() -> int:
    first = getpass.getpass('새 원격 접속 비밀번호를 입력하세요 (4자 이상): ')
    if len(first) < 4:
        print('비밀번호는 4자 이상이어야 합니다.')
        return 1
    second = getpass.getpass('같은 비밀번호를 한 번 더 입력하세요: ')
    if first != second:
        print('두 비밀번호가 일치하지 않습니다. 저장하지 않았습니다.')
        return 1

    try:
        config = json.loads(CONFIG.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        config = {}
    config['password'] = first
    config['cookie_key'] = secrets.token_urlsafe(32)
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG.with_name(f'.{CONFIG.name}.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(config) + '\n', encoding='utf-8')
    os.chmod(temporary, 0o600)
    os.replace(temporary, CONFIG)
    print('저장했습니다. 이전 기기의 로그인은 해제됐습니다.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
