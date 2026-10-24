"""Persistent shared browser profiles; loopback CDP, no copied user cookies."""
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from urllib.request import Request, urlopen
from urllib.parse import quote, urlsplit
import psutil
from .state import STATE, private_directory, write_json, exclusive
from . import providers, sessions

LOCK = threading.RLock()
PROFILE = STATE / 'browser-profile'
CONTROL = STATE / 'browser.json'
PREFERENCES = STATE / 'browser-preferences.json'


def selected():
    try:
        return json.loads(PREFERENCES.read_text())['browser_id']
    except (OSError, ValueError, KeyError):
        return 'chrome'  # Preserve the existing Chrome profile until explicitly changed.


def profile(key):
    return PROFILE if key == 'chrome' else STATE / 'browser-profiles' / key


def control(key):
    return CONTROL if key == 'chrome' else STATE / 'browsers' / (key + '.json')


def choose(key):
    providers.get(key)
    with LOCK, exclusive('browser-start'):
        write_json(PREFERENCES, {'browser_id': key})
    return status()


def _read(key=None):
    try:
        return json.loads(control(key or selected()).read_text())
    except (OSError, ValueError):
        return {}


def _owned(data, key=None):
    try:
        process = psutil.Process(data['pid'])
        return (abs(process.create_time() - data['created']) < .01
                and f'--user-data-dir={profile(key or selected())}' in process.cmdline())
    except (KeyError, psutil.Error, TypeError):
        return False


def _save(key, value):
    control(key).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_json(control(key), value)


def _debug_port(process, location):
    try:
        return int((location / 'DevToolsActivePort').read_text().splitlines()[0])
    except (OSError, ValueError, IndexError):
        # Older launcher attempts may have removed the file while Chrome was still alive.
        for connection in process.net_connections(kind='tcp'):
            if connection.status == psutil.CONN_LISTEN and connection.laddr.ip == '127.0.0.1':
                try:
                    if _version(connection.laddr.port).get('webSocketDebuggerUrl'):
                        return connection.laddr.port
                except (OSError, ValueError):
                    pass
    return 0


def _adopt(key):
    """Recover the real profile owner instead of a short-lived Chrome forwarding process."""
    spec = providers.get(key)
    data = _read(key)
    if _owned(data, key):
        return data
    expected = str(providers.executable(spec))
    for process in psutil.process_iter(['pid', 'cmdline', 'create_time']):
        try:
            args = process.info['cmdline'] or []
            if args and args[0] == expected and f'--user-data-dir={profile(key)}' in args:
                debug = next((arg.split('=', 1)[1] for arg in args if arg.startswith('--remote-debugging-port=')), None)
                port = int(debug) if debug else 0
                if debug == '0':
                    port = _debug_port(process, profile(key))
                data = {'pid': process.pid, 'created': process.info['create_time'], 'port': port,
                        'browser': spec['name'], 'mode': 'automation' if debug is not None else 'login'}
                _save(key, data)
                return data
        except (psutil.Error, OSError, ValueError, IndexError):
            continue
    return {}


def _version(port):
    with urlopen(f'http://127.0.0.1:{port}/json/version', timeout=1) as result:
        return json.load(result)


def _background(data, key):
    if not _owned(data, key):
        return False
    try:
        return any(arg == '--headless' or arg.startswith('--headless=')
                   for arg in psutil.Process(data['pid']).cmdline())
    except psutil.Error:
        return False


def status():
    with LOCK:
        key = selected()
        spec = providers.get(key, require_installed=False)
        installed = providers.executable(spec) is not None
        data = _adopt(key) if installed and spec['engine'] == 'chromium' else {}
        owned = _owned(data, key)
        if owned and not data.get('port'):
            try:
                data['port'] = int((profile(key) / 'DevToolsActivePort').read_text().splitlines()[0])
                _save(key, data)
            except (OSError, ValueError, IndexError):
                pass
        ready = False
        if owned and data.get('mode', 'automation') == 'automation':
            try:
                ready = bool(_version(data['port']).get('webSocketDebuggerUrl'))
            except (OSError, ValueError):
                pass
        manual = owned and data.get('mode') == 'login'
        return {'state': 'unavailable' if not installed else 'ready' if ready else 'login' if manual else 'starting' if owned else 'external' if spec['engine'] == 'external' else 'stopped',
                'endpoint': f"http://127.0.0.1:{data['port']}" if ready else '',
                'profile': str(profile(key)) if spec['engine'] == 'chromium' else '선택한 브라우저의 기존 프로필',
                'browser': spec['name'], 'browser_id': key, 'providers': providers.catalog(),
                'supports_automation': spec['engine'] == 'chromium', 'mode': data.get('mode', 'login'),
                'background': _background(data, key),
                'accounts': sessions.status(profile(key), spec['engine']), 'persistent': True}


def start(mode='login', url='about:blank'):
    with LOCK, exclusive('browser-start'):
        key = selected()
        spec = providers.get(key)
        executable = providers.executable(spec)
        if spec['engine'] != 'chromium':
            if mode == 'automation':
                raise ValueError('이 브라우저는 일반 로그인·가입 화면 열기만 지원합니다. 현재 공용 CDP 도구로 연결할 수 없습니다.')
            import sys
            command = ['/usr/bin/open', '-a', str(executable.parents[2]), url] if sys.platform == 'darwin' else [str(executable), url]
            subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return status()
        current = status()
        data = _read(key)
        background = mode == 'automation'
        if _owned(data, key) and (data.get('mode', 'automation') != mode
                                  or current['background'] != background):
            # Reuse the exact profile, including its saved login, when changing execution mode.
            process = psutil.Process(data['pid'])
            process.terminate()
            try:
                process.wait(timeout=8)
            except psutil.TimeoutExpired as error:
                raise ValueError('전용 브라우저가 종료를 기다리고 있습니다. 창을 직접 닫은 뒤 다시 누르세요.') from error
            current = status()
        if current['state'] in ('ready', 'login'):
            if mode == 'login':
                subprocess.Popen([str(executable), f'--user-data-dir={profile(key)}', '--new-window', url],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return current
        if current['state'] == 'starting':
            raise ValueError('공용 브라우저가 준비 중입니다. 잠시 뒤 다시 확인하세요.')
        private_directory()
        location = profile(key)
        location.mkdir(parents=True, exist_ok=True, mode=0o700)
        port = data.get('port', 0) if mode == 'automation' else 0
        if port and mode == 'automation':
            try:
                with socket.socket() as probe:
                    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    probe.bind(('127.0.0.1', port))
            except OSError as error:
                raise ValueError('공용 브라우저 포트를 다른 프로세스가 사용 중입니다. 기존 브라우저 창을 확인하세요.') from error
        active_port = location / 'DevToolsActivePort'
        if mode == 'automation':
            active_port.unlink(missing_ok=True)
        with (STATE / 'browser.log').open('ab') as log:
            os.chmod(STATE / 'browser.log', 0o600)
            flags = (['--remote-debugging-address=127.0.0.1', f'--remote-debugging-port={port}',
                      '--headless=new', '--restore-last-session'] if background else ['--new-window'])
            process = subprocess.Popen([
                str(executable), f'--user-data-dir={location}', *flags,
                '--no-first-run', '--no-default-browser-check', url],
                stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        created = psutil.Process(process.pid).create_time()
        _save(key, {'pid': process.pid, 'created': created,
                   'port': port, 'browser': spec['name'], 'mode': mode})
        if mode == 'login':
            return status()
        for _ in range(80):
            if process.poll() is not None:
                raise ValueError('공용 브라우저가 종료됐습니다. 기존 전용 프로필 창 또는 browser.log를 확인하세요.')
            try:
                actual_port = port or int(active_port.read_text().splitlines()[0])
                if _version(actual_port).get('webSocketDebuggerUrl'):
                    actual = _adopt(key)
                    if not actual:
                        raise ValueError('전용 브라우저 소유 프로세스를 확인하지 못했습니다.')
                    _save(key, {**actual, 'port': actual_port, 'mode': mode})
                    return status()
            except (OSError, ValueError, IndexError):
                pass
            time.sleep(.1)
        raise ValueError('브라우저 준비 시간이 초과됐습니다. 열린 창과 browser.log를 확인하세요.')


def public_url(value):
    parts = urlsplit(value)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
        raise ValueError('계정 정보가 포함되지 않은 HTTPS 업체 주소를 입력하세요.')
    import ipaddress
    host = parts.hostname.lower()
    if host == 'localhost' or '.' not in host or host.endswith(('.localhost', '.local', '.internal')):
        raise ValueError('외부 업체 주소를 입력하세요.')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return value
    raise ValueError('IP 주소 대신 공식 업체 도메인을 입력하세요.')


def open_page(url):
    url = public_url(url)
    with LOCK:
        if providers.get(selected())['engine'] != 'chromium':
            raise ValueError('자동 계정 작업은 공용 Chromium 브라우저가 필요합니다. 데스크톱 창은 자동으로 열지 않습니다.')
        current = start('automation')
        request = Request(current['endpoint'] + '/json/new?' + quote(url, safe=''), method='PUT')
        with urlopen(request, timeout=5) as result:
            target = json.load(result)
        return {'opened': True, 'tab_id': target['id'], 'url': url}
