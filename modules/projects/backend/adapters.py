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
    for filename in ('main.py', 'app.py', 'api.py', 'backend/main.py', 'backend/app.py', 'app/main.py', 'api/main.py', 'src/main.py'):
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
                        if ui: result['ui'] = ui
                        return validate(source, result)
    if ui:
        return validate(source, ui)
    project = source / 'pyproject.toml'
    if project.is_file():
        data = tomllib.loads(project.read_text(encoding='utf8'))
        scripts = data.get('project', {}).get('scripts', {})
        if len(scripts) == 1:
            return validate(source, {'kind': 'python-cli', 'directory': '.', 'entry': next(iter(scripts.values())), 'install': True})
    return None


def validate(source, spec):
    if spec.get('kind') == 'node-mcp':
        from .node_mcp import validate as validate_mcp
        return validate_mcp(source, spec)
    if spec.get('kind') not in ('static', 'vite', 'fastapi', 'python-cli', 'native'):
        raise ValueError('생성된 실행 어댑터 종류를 지원하지 않습니다.')
    folder = owned(source, spec.get('directory', '.'))
    if not folder.is_dir(): raise ValueError('실행 폴더가 없습니다.')
    if spec['kind'] in ('static', 'vite'):
        owned(folder, spec.get('output', 'dist' if spec['kind'] == 'vite' else '.'))
    if spec['kind'] in ('fastapi', 'python-cli'):
        if not re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*', spec.get('app') or spec.get('entry', '')):
            raise ValueError('Python 실행 진입점은 module:object 형식이어야 합니다.')
    if spec.get('ui'): validate(source, spec['ui'])
    return spec


def prepare(source, spec, run):
    folder = owned(source, spec.get('directory', '.'))
    kind = spec['kind']
    if kind == 'node-mcp':
        from .node_mcp import prepare as prepare_mcp
        prepare_mcp(source, spec, run)
    elif kind == 'vite':
        node = shutil.which('node')
        npm = Path(node or '').parent / 'node_modules/npm/bin/npm-cli.js'
        if not node or not npm.is_file(): raise ValueError('설치된 Node.js/npm을 찾지 못했습니다.')
        lock = folder / 'package-lock.json'
        run([node, str(npm), 'ci' if lock.is_file() else 'install', '--no-audit', '--no-fund'], folder, 900)
        run([node, str(npm), 'run', 'build', '--', '--base=./'], folder, 900)
    elif kind in ('fastapi', 'python-cli', 'native'):
        # Pin every existing distribution so a project cannot upgrade the finance/Hermes environment.
        from importlib.metadata import distributions
        constraints = source.parent / 'existing-python.txt'
        values = sorted({dist.metadata['Name'] + '==' + dist.version for dist in distributions() if dist.metadata['Name']})
        constraints.write_text('\n'.join(values), encoding='utf8')
        requirements = next((path for path in (folder / 'requirements.txt', source / 'requirements.txt') if path.is_file()), None)
        if kind == 'native':
            metadata = json.loads((source / 'module.json').read_text(encoding='utf8'))
            if metadata.get('requirements'): requirements = owned(source, metadata['requirements'])
        if requirements:
            run([sys.executable, '-m', 'pip', 'install', '-c', str(constraints), '-r', str(requirements)], folder, 900)
        if kind == 'python-cli' and spec.get('install'):
            run([sys.executable, '-m', 'pip', 'install', '-c', str(constraints), '-e', str(folder)], folder, 900)
    if kind in ('static', 'vite'):
        index = owned(owned(folder, spec.get('output', '.')), 'index.html')
        if not index.is_file(): raise ValueError('빌드 결과에 index.html이 없습니다.')
    if spec.get('ui'): prepare(source, spec['ui'], run)


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
