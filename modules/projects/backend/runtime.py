"""Share host resources and serve imported UI; do not create per-menu HTTP servers."""
import atexit
import base64
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from .store import owned, read

WORKERS = {}
LOCK = threading.RLock()
ACTIVE = 0
RESTARTING = False


class AppWorker:
    def __init__(self, source, spec, environment):
        self.lock = threading.Lock(); self.responses = queue.Queue(); self.source = str(source)
        folder = owned(source, spec.get('directory', '.'))
        log = source.parent / 'application.log'
        self.output = log.open('a', encoding='utf8')
        if spec['kind'] == 'node-mcp':
            from .node_mcp import command
            from platform_modules import ROOT
            python = ROOT / 'modules/hermes/.venv/Scripts/python.exe'
            if not python.is_file(): raise ValueError('공유 MCP Python 실행 환경이 없습니다.')
            arguments = [str(python), '-I', '-X', 'utf8', '-B', str(Path(__file__).with_name('mcp_worker.py')), json.dumps(command(source, spec))]
        else:
            from .python_packages import folder as packages
            arguments = [sys.executable, '-I', '-X', 'utf8', '-B', str(Path(__file__).with_name('app_worker.py')), str(folder), spec['app'], str(packages(source))]
        self.process = subprocess.Popen(arguments, cwd=folder, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.output,
            text=True, encoding='utf8', bufsize=1, env={**os.environ, **environment, 'PYTHONUTF8': '1'})
        self.reader = threading.Thread(target=self._read, daemon=True); self.reader.start()

    def _read(self):
        try:
            for line in self.process.stdout:
                try: self.responses.put(json.loads(line))
                except ValueError: pass
        finally: self.responses.put({'error': '프로젝트 실행기가 종료됐습니다. 실행 로그를 확인하세요.'})

    def call(self, payload):
        with self.lock:
            if self.process.poll() is not None: raise ValueError('프로젝트 실행기가 종료됐습니다.')
            self.process.stdin.write(json.dumps(payload) + '\n'); self.process.stdin.flush()
            try: result = self.responses.get(timeout=70)
            except queue.Empty:
                self.close(); raise ValueError('프로젝트 응답 시간이 초과됐습니다.')
            if result.get('error'): raise ValueError(result['error'])
            return result

    def close(self):
        if self.process.poll() is None:
            try:
                self.process.stdin.close(); self.process.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                self.process.kill(); self.process.wait(timeout=3)
        self.output.close()
        if self.process.stdin and not self.process.stdin.closed: self.process.stdin.close()
        self.reader.join(timeout=2)
        if self.process.stdout: self.process.stdout.close()


def busy_reason():
    with LOCK: return '실행 중인 외부 프로젝트 요청' if ACTIVE else ''


def invoke(record, payload):
    global ACTIVE
    source = Path(record['active_source']); spec = record['adapter']
    if spec['kind'] not in ('fastapi', 'node-mcp'): raise ValueError('이 프로젝트는 API/MCP 앱이 아닙니다.')
    with LOCK:
        if RESTARTING: raise ValueError('서버 적용 중입니다. 잠시 뒤 다시 실행하세요.')
        ACTIVE += 1
    try:
        key = record['id']
        with LOCK:
            worker = WORKERS.get(key)
            if worker and worker.source != str(source): worker.close(); worker = None
            if worker is None:
                worker = AppWorker(source, spec, record.get('environment', {})); WORKERS[key] = worker
        return worker.call(payload)
    finally:
        with LOCK: ACTIVE -= 1


def verify(source, spec, environment=None):
    if spec['kind']=='powershell':
        from .powershell_app import inspect
        inspect(source,spec)
    if spec['kind'] == 'node-mcp':
        worker = AppWorker(source, spec, environment or {})
        try:
            result = worker.call({'operation': 'list'})
            if not result.get('tools'): raise ValueError('실제로 연결된 MCP 도구가 없습니다.')
        finally: worker.close()
    if spec['kind'] == 'fastapi':
        worker = AppWorker(source, spec, environment or {})
        try:
            result = worker.call({'path': '/openapi.json', 'inspect': True})
            if result['status'] != 200: raise ValueError('FastAPI OpenAPI 실행 확인에 실패했습니다.')
            data = json.loads(base64.b64decode(result['body']))
            if not data.get('openapi') or not isinstance(data.get('paths'), dict): raise ValueError('올바른 API 응답이 아닙니다.')
            schemes = data.get('components', {}).get('securitySchemes', {}).values()
            if result.get('features', {}).get('cookie_sessions') or any(item.get('in') == 'cookie' for item in schemes):
                raise ValueError('쿠키 세션 앱은 현재 통로에 맞는 인증 어댑터가 필요합니다. 인증을 제거해서 통과시키지 마세요.')
        finally: worker.close()


def render_html(text, identifier, has_api, korean=False):
    import re
    base = '<base href="/assets/projects/' + identifier + '/">'
    if korean: base += '<script defer src="/assets/projects/' + identifier + '/_platform-language.js"></script>'
    bridge = '<script>' + Path(__file__).with_name('assets_bridge.js').read_text(encoding='utf8').replace('__PROJECT_ID__', json.dumps(identifier)) + '</script>' if has_api else ''
    text = re.sub(r'<base\b[^>]*>', '', text, flags=re.I)
    return re.sub(r'(<head\b[^>]*>)', lambda match: match[1] + base + bridge, text, count=1, flags=re.I) if '<head' in text.lower() else base + bridge + text


def verify_ui(source, spec, environment, run, project_id='verification'):
    ui = spec.get('ui') if spec['kind'] == 'fastapi' else spec
    if not ui or ui['kind'] not in ('static', 'vite'): return False
    import shutil
    root = owned(owned(source, ui.get('directory', '.')), ui.get('output', '.'))
    config = {'root': str(root), 'project_id': project_id,
        'python': sys.executable, 'environment': environment, 'screenshot': str(source.parent / 'ui-verification.png'),
        'index_html': render_html((root / 'index.html').read_text(encoding='utf8'), project_id, spec['kind'] == 'fastapi')}
    if spec['kind'] == 'fastapi':
        from .python_packages import folder as packages
        config['app'] = {'folder': str(owned(source, spec.get('directory', '.'))), 'target': spec['app'], 'packages': str(packages(source))}
    file = source.parent / 'ui-verification.json'; file.write_text(json.dumps(config), encoding='utf8')
    try: run([shutil.which('node'), str(Path(__file__).with_name('verify_ui.cjs')), str(file)], source, 90)
    finally: file.unlink(missing_ok=True)
    return True


def run_cli(record, arguments):
    global ACTIVE
    from .installer import run_command
    source = Path(record['active_source']); spec = record['adapter']
    if spec['kind'] != 'python-cli': raise ValueError('명령 실행 프로젝트가 아닙니다.')
    if not isinstance(arguments, list) or not all(isinstance(value, str) for value in arguments) or len(arguments) > 64:
        raise ValueError('실행 인수를 문자열 목록으로 전달하세요.')
    from .python_packages import cli_command
    command = cli_command(source, spec, arguments)
    log = source.parent / 'last-run.log'
    with LOCK:
        if RESTARTING: raise ValueError('서버 적용 중입니다.')
        ACTIVE += 1
    try:
        run_command(command, owned(source, spec.get('directory', '.')), log, threading.Event(), timeout=120,
            environment=record.get('environment', {}))
    finally:
        with LOCK: ACTIVE -= 1
    return {'text': log.read_text(encoding='utf8', errors='replace')[-30000:]}


def close():
    with LOCK:
        for worker in WORKERS.values(): worker.close()
        WORKERS.clear()


def register_host(app):
    @app.get('/assets/project-packages/{key}/{name}', include_in_schema=False)
    def package_download(key: str, name: str):
        from .store import STATE, identifier
        import re
        try:
            from .builtin_packages import SUPPORTED
            identifier(key)
            if key not in SUPPORTED: read(key)
            if not re.fullmatch(re.escape(key) + r'-[a-f0-9]{12}\.zip', name): raise ValueError('앱 패키지 이름이 올바르지 않습니다.')
            path = owned(STATE, 'projects/' + key + '/exports/' + name)
            if not path.is_file(): raise ValueError('내보낸 앱 파일이 없습니다.')
            return FileResponse(path, filename=name, media_type='application/zip', headers={'Cache-Control': 'no-store'})
        except ValueError as exc: raise HTTPException(404, str(exc)) from exc

    @app.get('/assets/projects/{identifier}/{path:path}', include_in_schema=False)
    def asset(identifier: str, path: str):
        try:
            record = read(identifier)
            if not record.get('active_source'): raise ValueError('아직 실행 가능한 설치본이 없습니다.')
            spec = record['adapter']; ui = spec.get('ui') if spec['kind'] == 'fastapi' else spec
            if not ui or ui['kind'] not in ('static', 'vite'): raise ValueError('원본 웹 화면이 없습니다.')
            if path == '_platform-language.js': return FileResponse(Path(__file__).with_name('project_language.js'), media_type='application/javascript')
            source = Path(record['active_source'])
            base = owned(owned(source, ui.get('directory', '.')), ui.get('output', '.'))
            file = owned(base, path or 'index.html')
            if any(part.startswith('.') for part in file.relative_to(base).parts):
                raise HTTPException(404, '이 파일은 웹 화면으로 제공하지 않습니다.')
            if not file.is_file() and '.' not in file.name: file = base / 'index.html'
            if not file.is_file(): raise HTTPException(404, '프로젝트 화면 파일이 없습니다.')
            if file.suffix.lower() == '.html':
                text = render_html(file.read_text(encoding='utf8'), identifier, spec['kind'] == 'fastapi', korean=True)
                return HTMLResponse(text, headers={'Cache-Control': 'no-store'})
            return FileResponse(file)
        except ValueError as exc: raise HTTPException(404, str(exc)) from exc


atexit.register(close)
