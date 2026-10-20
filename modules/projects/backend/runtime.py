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
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from .store import owned, read

WORKERS = {}
LOCK = threading.RLock()
ACTIVE = 0
CLI_ACTIVE = set()
RESTARTING = False


class AppWorker:
    def __init__(self, source, spec, environment, harness=None, project_id=None, integration=None, app_data=None):
        self.lock = threading.Lock(); self.responses = queue.Queue(); self.source = str(source)
        self.input_lock = threading.Lock(); self.harness_pending = {}; self.project_id = project_id; self.application_active=0
        folder = owned(source, spec.get('directory', '.'))
        log = source.parent / 'application.log'
        self.output = log.open('a', encoding='utf8')
        if spec['kind'] == 'node-mcp':
            from .node_mcp import command
            from platform_modules import ROOT
            python = ROOT / 'modules/hermes/.venv/Scripts/python.exe'
            if not python.is_file(): raise ValueError('공유 MCP Python 실행 환경이 없습니다.')
            arguments = [str(python), '-I', '-X', 'utf8', '-B', str(Path(__file__).with_name('mcp_worker.py')), json.dumps(command(source, spec))]
        elif spec['kind'] == 'node-http':
            import shutil
            node = shutil.which('node')
            if not node: raise ValueError('Node.js 실행 환경이 없습니다.')
            arguments = [node, str(Path(__file__).with_name('node_http_worker.cjs')), str(folder), spec['entry']]
        else:
            from .python_packages import folder as packages
            arguments = [sys.executable, '-I', '-X', 'utf8', '-B', str(Path(__file__).with_name('app_worker.py')), str(folder), spec['app'], str(packages(source))]
            arguments.append(harness['entry'] if harness and harness.get('enabled') else '')
            if integration: arguments.extend([str(integration),str(app_data)])
        self.process = subprocess.Popen(arguments, cwd=folder, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.output,
            text=True, encoding='utf8', bufsize=1, env={**os.environ, **environment, 'PYTHONUTF8': '1','PLATFORM_PROJECT_ID':project_id or ''})
        self.reader = threading.Thread(target=self._read, daemon=True); self.reader.start()

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    value = json.loads(line)
                    if 'application_activity' in value:
                        self.application_active=int(value['application_activity'])
                    elif 'harness_request' in value:
                        payload = value['harness_request']; cancelled = threading.Event()
                        self.harness_pending[payload['id']] = cancelled
                        threading.Thread(target=self._harness, args=(payload, cancelled), daemon=True).start()
                    elif 'harness_cancel' in value:
                        if event := self.harness_pending.get(value['harness_cancel']): event.set()
                    else: self.responses.put(value)
                except ValueError: pass
        finally: self.responses.put({'error': '프로젝트 실행기가 종료됐습니다. 실행 로그를 확인하세요.'})

    def _harness(self, payload, cancelled):
        response = {'harness_result': True, 'id': payload['id']}
        try:
            from .harness import execute
            if not self.project_id: raise ValueError('앱 하네스 소속이 없습니다.')
            response['text'] = execute(self.project_id, payload, cancelled)
        except Exception as exc: response['error'] = str(exc)
        finally:
            self.harness_pending.pop(payload['id'], None)
        try: self.send(response)
        except (OSError, ValueError): pass

    def send(self, payload):
        with self.input_lock:
            self.process.stdin.write(json.dumps(payload) + '\n'); self.process.stdin.flush()

    def call(self, payload):
        with self.lock:
            if self.process.poll() is not None: raise ValueError('프로젝트 실행기가 종료됐습니다.')
            self.send(payload)
            try: result = self.responses.get(timeout=70)
            except queue.Empty:
                self.close(); raise ValueError('프로젝트 응답 시간이 초과됐습니다.')
            if result.get('error'): raise ValueError(result['error'])
            return result

    def close(self):
        for cancelled in list(self.harness_pending.values()): cancelled.set()
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
    from . import harness
    with LOCK:
        active=ACTIVE
        background=any(worker.application_active and worker.process.poll() is None for worker in WORKERS.values())
    return '실행 중인 외부 프로젝트 요청' if active else '실행 중인 앱 제작·검증 작업' if background else harness.busy_reason()


def invoke(record, payload, origin=None):
    global ACTIVE
    source = Path(record['active_source']); spec = record['adapter']
    if spec['kind'] not in ('fastapi', 'node-mcp', 'node-http'): raise ValueError('이 프로젝트는 API/MCP 앱이 아닙니다.')
    with LOCK:
        if RESTARTING: raise ValueError('서버 적용 중입니다. 잠시 뒤 다시 실행하세요.')
        from .installer import JOBS
        if record['id'] in JOBS: raise ValueError('이 앱을 업데이트 중입니다. 완료한 뒤 다시 실행하세요.')
        ACTIVE += 1
    try:
        key = record['id']
        with LOCK:
            worker = WORKERS.get(key)
            if worker and worker.source != str(source): worker.close(); worker = None
            if worker is None:
                from .workspaces import adapter
                from .store import project_folder
                worker = AppWorker(source, spec, record.get('environment', {}), record.get('harness'), key, adapter(record), project_folder(record)); WORKERS[key] = worker
        forwarded = {**payload, '_host': origin.headers.get('host', '') if origin else '',
            '_client': [origin.client.host, origin.client.port] if origin and origin.client else ['platform-internal', 0],
            '_server': [origin.url.hostname, origin.url.port or 80] if origin else ['127.0.0.1', 8766]}
        return worker.call(forwarded)
    finally:
        with LOCK: ACTIVE -= 1


def verify(source, spec, environment=None):
    if spec['kind'] == 'node-http':
        worker = AppWorker(source, spec, environment or {})
        try:
            result = worker.call({'path': '/'})
            if result['status'] >= 500: raise ValueError('Node 서버 실행 확인에 실패했습니다.')
        finally: worker.close()
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
    if has_api:
        text = re.sub(r'((?:href|src|action)\s*=\s*[\"\'])/(?!/)', lambda m: m[1] + '/assets/projects/' + identifier + '/', text, flags=re.I)
    return re.sub(r'(<head\b[^>]*>)', lambda match: match[1] + base + bridge, text, count=1, flags=re.I) if '<head' in text.lower() else base + bridge + text


def verify_ui(source, spec, environment, run, project_id='verification'):
    ui = spec.get('ui') if spec['kind'] in ('fastapi', 'node-http') else spec
    if not ui or ui['kind'] not in ('static', 'vite', 'asgi'): return False
    import shutil
    root = owned(owned(source, ui.get('directory', '.')), ui.get('output', '.'))
    server_ui = ui['kind'] == 'asgi'
    if server_ui:
        worker = AppWorker(source, spec, environment)
        try:
            result = worker.call({'path': '/'})
            if result['status'] != 200 or 'text/html' not in result.get('headers', {}).get('content-type', ''):
                raise ValueError('원본 서버의 첫 화면 실행 확인에 실패했습니다.')
            index = base64.b64decode(result['body']).decode('utf8')
        finally: worker.close()
    else: index = (root / 'index.html').read_text(encoding='utf8')
    config = {'root': str(root), 'project_id': project_id, 'server_ui': server_ui,
        'python': sys.executable, 'environment': environment, 'screenshot': str(source.parent / 'ui-verification.png'),
        'index_html': render_html(index, project_id, spec['kind'] in ('fastapi', 'node-http'))}
    if spec['kind'] == 'node-http':
        config['node_app'] = {'folder': str(owned(source, spec.get('directory', '.'))), 'entry': spec['entry']}
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
        if record['id'] in CLI_ACTIVE:raise ValueError('이 프로젝트의 실행이 끝난 뒤 다시 실행하세요.')
        CLI_ACTIVE.add(record['id'])
        ACTIVE += 1
    try:
        log.write_text('',encoding='utf8')
        run_command(command, owned(source, spec.get('directory', '.')), log, threading.Event(), timeout=120,
            environment=record.get('environment', {}))
    finally:
        with LOCK:
            ACTIVE -= 1
            CLI_ACTIVE.discard(record['id'])
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
            from .store import project_folder
            path = owned(project_folder(read(key) if key not in SUPPORTED else {'id': key}), 'exports/' + name)
            if not path.is_file(): raise ValueError('내보낸 앱 파일이 없습니다.')
            return FileResponse(path, filename=name, media_type='application/zip', headers={'Cache-Control': 'no-store'})
        except ValueError as exc: raise HTTPException(404, str(exc)) from exc

    @app.get('/assets/projects/{identifier}/{path:path}', include_in_schema=False)
    def asset(identifier: str, path: str, request: Request):
        try:
            record = read(identifier)
            if not record.get('active_source'): raise ValueError('아직 실행 가능한 설치본이 없습니다.')
            spec = record['adapter']; ui = spec.get('ui') if spec['kind'] in ('fastapi', 'node-http') else spec
            if not ui or ui['kind'] not in ('static', 'vite', 'asgi'): raise ValueError('원본 웹 화면이 없습니다.')
            if path.startswith('_platform-output/'):
                from .store import project_folder
                relative=path.removeprefix('_platform-output/')
                parts=Path(relative).parts
                if len(parts)<2 or any(part.startswith('.') or part=='node_modules' for part in parts) or not (parts[1]=='dist' or len(parts)==2 and parts[1] in ('requirements.md','verification.json')):
                    raise ValueError('공개된 작업 결과 경로가 아닙니다.')
                file=owned(project_folder(record)/'workspaces',relative)
                if not file.is_file(): raise ValueError('생성된 결과 파일이 없습니다.')
                return FileResponse(file,headers={'Cache-Control':'no-store'})
            if path == '_platform-workspace.html':
                from .workspaces import document
                return HTMLResponse(render_html(document(record), identifier, True), headers={'Cache-Control': 'no-store'})
            if path == '_platform-language.js': return FileResponse(Path(__file__).with_name('project_language.js'), media_type='application/javascript')
            if ui['kind'] == 'asgi':
                result = invoke(record, {'path': '/' if path in ('', 'index.html') else '/' + path,
                    'query': request.url.query, 'method': 'GET', 'headers': dict(request.headers)}, request)
                headers = {k: v for k, v in result.get('headers', {}).items() if k.lower() not in ('content-length', 'content-encoding', 'connection')}
                headers['Cache-Control'] = 'no-store'
                body = base64.b64decode(result['body'])
                if 'text/html' in headers.get('content-type', ''):
                    body = render_html(body.decode('utf8'), identifier, True, korean=True).encode('utf8')
                if headers.get('location', '').startswith('/'):
                    headers['location'] = '/assets/projects/' + identifier + headers['location']
                return Response(body, status_code=result['status'], headers=headers)
            source = Path(record['active_source'])
            base = owned(owned(source, ui.get('directory', '.')), ui.get('output', '.'))
            file = owned(base, path or 'index.html')
            if any(part.startswith('.') for part in file.relative_to(base).parts):
                raise HTTPException(404, '이 파일은 웹 화면으로 제공하지 않습니다.')
            if not file.is_file() and '.' not in file.name: file = base / 'index.html'
            if not file.is_file(): raise HTTPException(404, '프로젝트 화면 파일이 없습니다.')
            if file.suffix.lower() == '.html':
                text = render_html(file.read_text(encoding='utf8'), identifier, spec['kind'] in ('fastapi', 'node-http'), korean=True)
                return HTMLResponse(text, headers={'Cache-Control': 'no-store'})
            return FileResponse(file, headers={'Cache-Control': 'no-store'})
        except ValueError as exc: raise HTTPException(404, str(exc)) from exc


atexit.register(close)
