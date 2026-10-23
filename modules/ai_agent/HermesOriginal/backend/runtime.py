"""Own only the original dashboard process, never its features or agent loop."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import psutil
from urllib.request import urlopen
from .launch import BASE, HOME, SOURCE, environment

LOCK = threading.RLock()
STATE = BASE / 'server.json'
READY = BASE / 'server-ready.json'
_process = None


def _read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _identity(pid):
    if os.name != 'posix':
        return ''
    result = subprocess.run(['/bin/ps', '-p', str(pid), '-o', 'lstart=', '-o', 'args='],
                            capture_output=True, text=True)
    text = result.stdout.strip()
    return text if str(SOURCE / 'hermes') in text else ''


def _adopt_dashboard(port, state):
    """An upstream update can replace its dashboard PID; verify before adopting."""
    if os.name != 'posix' or type(port) is not int or not 0 < port < 65536:
        return state
    try:
        listeners = subprocess.run(['lsof', '-nP', f'-iTCP:{port}', '-sTCP:LISTEN', '-t'],
                                   capture_output=True, text=True, timeout=3)
        for value in set(listeners.stdout.split()):
            pid = int(value)
            identity = _identity(pid)
            if not identity:
                continue
            process = psutil.Process(pid)
            home = Path(process.environ().get('HERMES_HOME', '')).resolve()
            if not home.is_relative_to(HOME.resolve()) or Path(process.cwd()).resolve() != SOURCE.resolve():
                continue
            with urlopen(f'http://127.0.0.1:{port}/api/status', timeout=2) as response:
                facts = json.load(response)
            if not isinstance(facts, dict) or 'active_sessions' not in facts:
                continue
            state = {**state, 'pid': pid, 'identity': identity, 'port': port}
            STATE.write_text(json.dumps(state))
            os.chmod(STATE, 0o600)
            return state
    except (OSError, ValueError, subprocess.SubprocessError, psutil.Error):
        pass
    return state


def status():
    with LOCK:
        state = _read(STATE)
        port = _read(READY).get('port') or state.get('port')
        pid = state.get('pid')
        alive = bool(pid and _identity(pid) == state.get('identity') and state.get('identity'))
        if not alive:
            state = _adopt_dashboard(port, state)
            pid = state.get('pid')
            alive = bool(pid and _identity(pid) == state.get('identity') and state.get('identity'))
        if not alive:
            port = None
        url = f'http://127.0.0.1:{port}/' if isinstance(port, int) and 0 < port < 65536 else ''
        ready = False
        if url:
            try:
                with urlopen(url, timeout=1) as response:
                    ready = response.status == 200
            except OSError:
                pass
        return {'state': 'ready' if ready else 'starting' if alive else 'stopped',
                'url': url if ready else '', 'revision': state.get('revision', ''),
                'source': str(SOURCE), 'home': str(HOME),
                'log': str(BASE / 'dashboard.log')}


def start():
    global _process
    with LOCK:
        current = status()
        if current['state'] != 'stopped':
            return current
        if not (SOURCE / '.git').exists():
            raise ValueError('Hermes 공식 원본 체크아웃을 먼저 설치하세요.')
        BASE.mkdir(parents=True, exist_ok=True)
        HOME.mkdir(parents=True, exist_ok=True)
        # Keep the browser origin stable so native language/theme preferences survive restarts.
        previous_port = _read(READY).get('port') or _read(STATE).get('port')
        port = previous_port if type(previous_port) is int and 0 < previous_port < 65536 else 0
        READY.unlink(missing_ok=True)
        env = environment()
        env['HERMES_DESKTOP_READY_FILE'] = str(READY)
        with (BASE / 'dashboard.log').open('ab') as log:
            os.chmod(log.name, 0o600)
            _process = subprocess.Popen([sys.executable, str(Path(__file__).with_name('launch.py')),
                'dashboard', '--no-open', '--isolated', '--host', '127.0.0.1', '--port', str(port)],
                cwd=SOURCE, env=env, stdout=log, stderr=log, start_new_session=True)
        # exec replaces the launcher PID. Store its actual command identity before publishing.
        identity = ''
        for _ in range(100):
            identity = _identity(_process.pid)
            if identity or _process.poll() is not None:
                break
            time.sleep(.1)
        if not identity:
            raise RuntimeError('원본 실행기 기동 실패: dashboard.log를 확인하세요.')
        revision = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
        STATE.write_text(json.dumps({'pid': _process.pid, 'identity': identity,
                                     'revision': revision, 'port': port}))
        os.chmod(STATE, 0o600)
        return status()


def stop():
    with LOCK:
        state = _read(STATE)
        if state.get('identity') and _identity(state.get('pid')) == state['identity']:
            pid = state['pid']
            if os.getpgid(pid) == pid:
                os.killpg(pid, signal.SIGTERM)
            else:
                os.kill(pid, signal.SIGTERM)
            for _ in range(100):
                if not _identity(state['pid']):
                    break
                time.sleep(.1)
            if _identity(state['pid']):
                raise RuntimeError('원본이 종료 중입니다. 실행 중인 작업을 확인하세요.')
        return status()
