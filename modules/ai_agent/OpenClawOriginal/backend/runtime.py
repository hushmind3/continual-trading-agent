"""Own only the local OpenClaw Gateway process, not its internal features."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'runtime/ai_agent/OpenClawOriginal'
SOURCE = BASE / 'source'
HOME = BASE / 'home'
PORT = 19021
URL = f'http://127.0.0.1:{PORT}/'
STATE = BASE / 'server.json'
LOCK = threading.RLock()
_process = None


def _read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _identity(pid):
    if os.name != 'posix' or not isinstance(pid, int) or pid <= 0:
        return ''
    result = subprocess.run(['/bin/ps', '-p', str(pid), '-o', 'lstart=', '-o', 'args='],
                            capture_output=True, text=True)
    text = result.stdout.strip()
    return text if str(SOURCE / 'scripts/run-node.mjs') in text else ''


def _reachable():
    try:
        with urlopen(URL, timeout=1) as response:
            return response.status < 500
    except HTTPError as error:
        return error.code in (401, 403)
    except OSError:
        return False


def status():
    with LOCK:
        state = _read(STATE)
        pid = state.get('pid')
        alive = bool(state.get('identity') and _identity(pid) == state['identity'])
        ready = alive and _reachable()
        return {
            'state': 'ready' if ready else 'starting' if alive else 'stopped',
            'url': URL if ready else '',
            'revision': state.get('revision', ''),
            'source': str(SOURCE),
            'home': str(HOME),
            'log': str(BASE / 'dashboard.log'),
        }


def start():
    global _process
    with LOCK:
        current = status()
        if current['state'] != 'stopped':
            return current
        if not (SOURCE / 'package.json').is_file():
            raise ValueError('OpenClaw 공식 원본을 먼저 내려받으세요.')
        HOME.mkdir(parents=True, exist_ok=True)
        STATE.unlink(missing_ok=True)
        log_path = BASE / 'dashboard.log'
        with log_path.open('ab') as log:
            os.chmod(log_path, 0o600)
            _process = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve().with_name('launch.py')),
                 'gateway', 'run', '--bind', 'loopback', '--port', str(PORT)],
                cwd=SOURCE, stdout=log, stderr=log, start_new_session=True)
        identity = ''
        for _ in range(100):
            identity = _identity(_process.pid)
            if identity or _process.poll() is not None:
                break
            time.sleep(.1)
        if not identity:
            raise RuntimeError('OpenClaw 실행에 실패했습니다. dashboard.log를 확인하세요.')
        revision = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'],
                                           text=True).strip()
        STATE.write_text(json.dumps({'pid': _process.pid, 'identity': identity,
                                     'revision': revision}))
        os.chmod(STATE, 0o600)
        return status()


def stop():
    with LOCK:
        state = _read(STATE)
        pid = state.get('pid')
        if state.get('identity') and _identity(pid) == state['identity']:
            # Popen starts a private session; the Gateway is a child of the CLI.
            os.killpg(pid, signal.SIGTERM)
            for _ in range(100):
                if not _identity(pid) and not _reachable():
                    break
                time.sleep(.1)
            if _identity(pid) or _reachable():
                raise RuntimeError('OpenClaw가 종료 중입니다. 실행 로그를 확인하세요.')
        STATE.unlink(missing_ok=True)
        return status()
