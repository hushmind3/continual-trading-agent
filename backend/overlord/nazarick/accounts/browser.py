"""Persistent, visible Chrome profile; loopback CDP, no copied user cookies."""
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
from platform_native import browser_executable
from .state import STATE, private_directory, write_json, exclusive

LOCK = threading.RLock()
PROFILE = STATE / 'browser-profile'
CONTROL = STATE / 'browser.json'


def _read():
    try:
        return json.loads(CONTROL.read_text())
    except (OSError, ValueError):
        return {}


def _owned(data):
    try:
        process = psutil.Process(data['pid'])
        return (abs(process.create_time() - data['created']) < .01
                and f'--user-data-dir={PROFILE}' in process.cmdline())
    except (KeyError, psutil.Error, TypeError):
        return False


def _version(port):
    with urlopen(f'http://127.0.0.1:{port}/json/version', timeout=1) as result:
        return json.load(result)


def status():
    with LOCK:
        data = _read()
        owned = _owned(data)
        if owned and not data.get('port'):
            try:
                data['port'] = int((PROFILE / 'DevToolsActivePort').read_text().splitlines()[0])
                write_json(CONTROL, data)
            except (OSError, ValueError, IndexError):
                pass
        ready = False
        if owned:
            try:
                ready = bool(_version(data['port']).get('webSocketDebuggerUrl'))
            except (OSError, ValueError):
                pass
        return {'state': 'ready' if ready else 'starting' if owned else 'stopped',
                'endpoint': f"http://127.0.0.1:{data['port']}" if ready else '',
                'profile': str(PROFILE), 'browser': data.get('browser', ''),
                'login': '로그인 여부는 브라우저에서 확인', 'persistent': True}


def start():
    with LOCK, exclusive('browser-start'):
        current = status()
        if current['state'] == 'ready':
            return current
        if current['state'] == 'starting':
            raise ValueError('공용 브라우저가 준비 중입니다. 잠시 뒤 다시 확인하세요.')
        executable = browser_executable('chrome') or browser_executable('edge')
        if not executable:
            raise ValueError('설치된 Chrome 또는 Edge가 필요합니다.')
        private_directory()
        PROFILE.mkdir(exist_ok=True, mode=0o700)
        port = _read().get('port', 0)
        if port:
            try:
                with socket.socket() as probe:
                    probe.bind(('127.0.0.1', port))
            except OSError as error:
                raise ValueError('공용 브라우저 포트를 다른 프로세스가 사용 중입니다. 기존 브라우저 창을 확인하세요.') from error
        active_port = PROFILE / 'DevToolsActivePort'
        active_port.unlink(missing_ok=True)
        with (STATE / 'browser.log').open('ab') as log:
            os.chmod(STATE / 'browser.log', 0o600)
            process = subprocess.Popen([
                str(executable), f'--user-data-dir={PROFILE}',
                '--remote-debugging-address=127.0.0.1', f'--remote-debugging-port={port}',
                '--no-first-run', '--no-default-browser-check', '--new-window', 'about:blank'],
                stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        created = psutil.Process(process.pid).create_time()
        write_json(CONTROL, {'pid': process.pid, 'created': created,
                             'port': port, 'browser': executable.name})
        for _ in range(80):
            if process.poll() is not None:
                raise ValueError('공용 브라우저가 종료됐습니다. 기존 전용 프로필 창 또는 browser.log를 확인하세요.')
            try:
                actual_port = port or int(active_port.read_text().splitlines()[0])
                if _version(actual_port).get('webSocketDebuggerUrl'):
                    write_json(CONTROL, {'pid': process.pid, 'created': created,
                                        'port': actual_port, 'browser': executable.name})
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
        current = start()
        request = Request(current['endpoint'] + '/json/new?' + quote(url, safe=''), method='PUT')
        with urlopen(request, timeout=5) as result:
            target = json.load(result)
        return {'opened': True, 'tab_id': target['id'], 'url': url}
