"""Find real entry points before asking the existing agent to create an adapter."""
import ast
import json
from pathlib import Path
import re
import shutil
import sys
import tomllib
from .store import owned


def detect(source):
    descriptor = source / 'platform-project.json'
    if descriptor.is_file():
        return validate(source, json.loads(descriptor.read_text(encoding='utf8')))
    if (source / 'module.json').is_file():
        return {'kind': 'native', 'directory': '.'}
    from . import node_mcp
    if spec := node_mcp.detect(source): return spec
    # A Vite frontend can belong to a Node HTTP app; do not discard its server.
    package = source / 'package.json'
    node_app = None
    if package.is_file():
        scripts = json.loads(package.read_text(encoding='utf8')).get('scripts', {})
        for name in ('start', 'server'):
            match = re.fullmatch(r'node\s+[\"\']?([\w./-]+\.(?:js|mjs|cjs))[\"\']?', scripts.get(name, '').strip())
            if match and owned(source, match[1]).is_file():
                node_app = {'kind': 'node-http', 'directory': '.', 'entry': match[1]}
                break
    candidates = [source, *(source / name for name in ('frontend', 'web', 'client', 'app', 'ui', 'site', 'public', 'docs'))]
    ui = None
    for folder in candidates:
        package = folder / 'package.json'
        if package.is_file():
            data = json.loads(package.read_text(encoding='utf8'))
            deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
            if 'vite' in deps and data.get('scripts', {}).get('build'):
                ui = {'kind': 'vite', 'directory': folder.relative_to(source).as_posix(), 'output': 'dist'}
                break
        if (folder / 'index.html').is_file():
            ui = {'kind': 'static', 'directory': folder.relative_to(source).as_posix(), 'output': '.'}
    for filename in ('main.py', 'app.py', 'server.py', 'api.py', 'backend/main.py', 'backend/app.py', 'app/main.py', 'api/main.py', 'src/main.py'):
        file = source / filename
        if not file.is_file():
            continue
        tree = ast.parse(file.read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                call = node.value.func
                if (isinstance(call, ast.Name) and call.id == 'FastAPI') or (isinstance(call, ast.Attribute) and call.attr == 'FastAPI'):
                    name = next((target.id for target in node.targets if isinstance(target, ast.Name)), None)
                    if name:
                        result = {'kind': 'fastapi', 'directory': str(file.parent.relative_to(source)).replace('\\', '/'), 'app': file.stem + ':' + name}
                        # A server-rendered home page owns the UI; docs may be an old demo.
                        server_home = any(isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and
                            any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and
                                d.func.attr == 'get' and d.args and isinstance(d.args[0], ast.Constant) and d.args[0].value == '/' and
                                any(k.arg == 'response_class' and isinstance(k.value, ast.Name) and k.value.id in ('HTMLResponse', 'FileResponse') for k in d.keywords)
                                for d in item.decorator_list) for item in tree.body)
                        if server_home: result['ui'] = {'kind': 'asgi'}
                        elif ui: result['ui'] = ui
                        return validate(source, result)
    if node_app:
        if ui: node_app['ui'] = ui
        return validate(source, node_app)
    if ui:
        return validate(source, ui)
    from . import powershell_app
    if spec := powershell_app.detect(source): return spec
    project = source / 'pyproject.toml'
    if project.is_file():
        data = tomllib.loads(project.read_text(encoding='utf8'))
        scripts = data.get('project', {}).get('scripts', {})
        if len(scripts) == 1:
            return validate(source, {'kind': 'python-cli', 'directory': '.', 'entry': next(iter(scripts.values())), 'install': True})
    from .cli_schema import discover
    if spec:=discover(source):return validate(source,spec)
    return None


def validate(source, spec):
    if spec.get('kind') == 'node-mcp':
        from .node_mcp import validate as validate_mcp
        return validate_mcp(source, spec)
    if spec.get('kind') not in ('static', 'vite', 'fastapi', 'python-cli', 'native','powershell', 'node-http'):
        raise ValueError('생성된 실행 어댑터 종류를 지원하지 않습니다.')
    folder = owned(source, spec.get('directory', '.'))
    if not folder.is_dir(): raise ValueError('실행 폴더가 없습니다.')
    if spec['kind'] == 'node-http':
        entry = owned(folder, spec.get('entry', ''))
        if not entry.is_file() or entry.suffix not in ('.js', '.mjs', '.cjs'): raise ValueError('Node 서버 진입점이 없습니다.')
    if spec['kind']=='powershell':
        script=owned(source,spec.get('script',''))
        if not script.is_file() or script.suffix.lower()!='.ps1':raise ValueError('원본 설치 스크립트가 없습니다.')
    if spec['kind'] in ('static', 'vite'):
        owned(folder, spec.get('output', 'dist' if spec['kind'] == 'vite' else '.'))
    if spec['kind'] in ('fastapi', 'python-cli'):
        if spec['kind']=='python-cli' and spec.get('script'):
            script=owned(source,spec['script'])
            if not script.is_file() or script.suffix!='.py':raise ValueError('Python 실행 스크립트가 없습니다.')
        elif not re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*', spec.get('app') or spec.get('entry', '')):
            raise ValueError('Python 실행 진입점은 module:object 형식이어야 합니다.')
    if spec.get('ui'):
        if spec['ui'].get('kind') == 'asgi':
            if spec['kind'] != 'fastapi': raise ValueError('서버 화면에는 FastAPI 실행 진입점이 필요합니다.')
        else: validate(source, spec['ui'])
    return spec


def prepare(source, spec, run, reuse=False):
    folder = owned(source, spec.get('directory', '.'))
    kind = spec['kind']
    if kind == 'node-http' and spec.get('ui', {}).get('directory', '.') == spec.get('directory', '.') and spec.get('ui', {}).get('kind') == 'vite':
        prepare(source, spec['ui'], run, reuse=reuse)
        return
    if kind=='powershell':
        from .powershell_app import inspect
        inspect(source,spec)
    if kind == 'node-mcp':
        from .node_mcp import prepare as prepare_mcp
        prepare_mcp(source, spec, run)
    elif kind in ('vite', 'node-http'):
        node = shutil.which('node')
        npm = Path(node or '').parent / 'node_modules/npm/bin/npm-cli.js'
        if not node or not npm.is_file(): raise ValueError('설치된 Node.js/npm을 찾지 못했습니다.')
        lock = folder / 'package-lock.json'
        if not (reuse and (folder / 'node_modules').is_dir()):
            run([node, str(npm), 'ci' if lock.is_file() else 'install', '--no-audit', '--no-fund'], folder, 900)
        if kind == 'vite' and not (reuse and (folder / spec.get('output', 'dist') / 'index.html').is_file()):
            run([node, str(npm), 'run', 'build', '--', '--base=./'], folder, 900)
    elif kind in ('fastapi', 'python-cli', 'native'):
        from .python_packages import prepare as prepare_python
        prepare_python(source, spec, run)
    if kind in ('static', 'vite'):
        index = owned(owned(folder, spec.get('output', '.')), 'index.html')
        if not index.is_file(): raise ValueError('빌드 결과에 index.html이 없습니다.')
    if spec.get('ui') and spec['ui'].get('kind') != 'asgi': prepare(source, spec['ui'], run, reuse=reuse)


def generate_with_hermes(source, note, cancelled, progress, project_id='verification'):
    from ai_agent.Hermes.engine.bridge import bridge
    from .agent_setup import ensure_ready
    ensure_ready(bridge, cancelled, progress)
    prompt = (
        f'Install this project into the host: {source}. Read its README and actual entry points. '
        'Reuse its original UI and engine. Only modify files INSIDE this project. '
        'Create platform-project.json at the project root with a verified executable adapter. '
        'JSON kinds: static {directory,output}, vite {directory,output}, fastapi {directory,app:"module:app",'
        'ui:optional static/vite descriptor}, python-cli {directory,entry:"module:function",install:true}. '
        'Paths must be relative to the project. Do not start HTTP servers. Do not modify the host, '
        f'The UI mounts at /assets/projects/{project_id}/index.html, not at /. Configure client routing '
        'and asset paths for that mount (HashRouter is supported). Only fetch JSON API calls are bridged. '
        'Cookie sessions, WebSockets and streaming need a compatible adapter; do not claim unsupported '
        'features work. Never remove authentication or validation just to pass installation. '
        'shared environments, or install a different Python. You may adapt this source to these contracts. '
        'If impossible, report the missing requirement honestly; do not create a fake success. '
        'The host will install declared dependencies, build, and independently execute the entry. '
        f'Detection/build evidence: {note[:4000]}'
    )
    result = bridge.call('chat', {'message': prompt, 'workspace': str(source), 'read_only': False})
    progress('adapter', 'Hermes가 실행 방법과 연결 어댑터를 구성하고 있습니다.', agent_session=result.get('job', {}).get('session_id') or result.get('session_id') or result.get('id'))
    import time
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        if cancelled.is_set():
            bridge.call('stop'); raise ValueError('설치를 취소했습니다.')
        state = bridge.call('status')['job']
        if state.get('state') not in ('starting', 'running', 'stopping'):
            if state.get('state') != 'complete':
                raise ValueError(state.get('error') or '자동 어댑터 생성이 완료되지 않았습니다.')
            descriptor = source / 'platform-project.json'
            if not descriptor.is_file(): raise ValueError('모델이 실행 가능한 어댑터를 생성하지 못했습니다.')
            return validate(source, json.loads(descriptor.read_text(encoding='utf8')))
        time.sleep(1)
    bridge.call('stop')
    raise ValueError('자동 변환 시간이 초과됐습니다. 생성 기록은 Hermes 대화에서 확인할 수 있습니다.')
