"""Self-contained launcher copied into exported apps. Python standard library only."""
import argparse
import functools
import http.server
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent


def inside(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()): raise ValueError('앱 폴더 밖의 경로입니다.')
    return path


def python():
    return ROOT / '.runtime/venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def execute(command, work):
    subprocess.run([str(item) for item in command], cwd=work, check=True)


def npm():
    node = shutil.which('node')
    if not node: raise ValueError('Node.js를 설치한 다음 다시 실행하세요.')
    for path in (Path(node).parent / 'node_modules/npm/bin/npm-cli.js', Path(node).resolve().parent.parent / 'lib/node_modules/npm/bin/npm-cli.js'):
        if path.is_file(): return [node, str(path)]
    command = shutil.which('npm')
    if command: return [command]
    raise ValueError('npm을 찾지 못했습니다.')


def prepare(source, spec):
    work = inside(source, spec.get('directory', '.'))
    kind = spec['kind']
    if kind == 'node-http' and spec.get('ui', {}).get('kind') == 'vite' and spec['ui'].get('directory', '.') == spec.get('directory', '.'):
        prepare(source, spec['ui']); return
    if kind == 'node-mcp':
        target = source / '.platform-runtime'; target.mkdir(exist_ok=True)
        execute([*npm(), 'install', '--prefix', target, '--no-audit', '--no-fund', '--save-exact', spec['package'] + '@' + spec['version']], source)
    elif kind in ('vite', 'node-http'):
        execute([*npm(), 'ci' if (work / 'package-lock.json').is_file() else 'install', '--no-audit', '--no-fund'], work)
        if kind == 'vite': execute([*npm(), 'run', 'build', '--', '--base=./'], work)
    elif kind in ('fastapi', 'python-cli'):
        if not python().is_file(): venv.EnvBuilder(with_pip=True).create(python().parent.parent)
        requirements = next((path for path in (work / 'requirements.txt', source / 'requirements.txt') if path.is_file()), None)
        if requirements: execute([python(), '-m', 'pip', 'install', '-r', requirements], work)
        if (work / 'pyproject.toml').is_file(): execute([python(), '-m', 'pip', 'install', work], work)
        if kind == 'fastapi': execute([python(), '-m', 'pip', 'install', 'fastapi', 'uvicorn'], work)
    if spec.get('ui') and spec['ui'].get('kind') != 'asgi': prepare(source, spec['ui'])


def node_command(source, spec):
    root = inside(source / '.platform-runtime/node_modules', spec['package'])
    script = inside(root, spec['script'])
    if not script.is_file(): raise ValueError('먼저 python run.py setup을 실행하세요.')
    node = shutil.which('node')
    if not node: raise ValueError('Node.js를 찾지 못했습니다.')
    return [node, str(script), *spec['arguments']]


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'): stream.reconfigure(encoding='utf8')
    parser = argparse.ArgumentParser(description='플랫폼 없이 원본 앱을 실행합니다.')
    parser.add_argument('command', choices=['setup', 'run', 'check', 'mcp-config'], nargs='?', default='run')
    parser.add_argument('--port', type=int, default=8080)
    args, extra = parser.parse_known_args()
    metadata = json.loads((ROOT / 'app-package.json').read_text(encoding='utf8'))
    source = ROOT / 'source'; spec = metadata['adapter']; kind = spec['kind']
    private=ROOT/'.runtime/environment.json'
    if private.is_file():os.environ.update(json.loads(private.read_text(encoding='utf8')))
    work = inside(source, spec.get('directory', '.'))
    if args.command == 'setup': prepare(source, spec); return
    if args.command == 'check':
        inside(work, spec.get('output', 'index.html'))
        if kind in ('static', 'vite') and not inside(work, spec.get('output', '.')).joinpath('index.html').is_file():
            raise ValueError('빌드된 웹 화면이 없습니다. setup을 실행하세요.')
        if kind == 'node-mcp': node_command(source, spec)
        if kind == 'node-http' and not inside(work, spec['entry']).is_file():
            raise ValueError('원본 Node 서버 진입점이 없습니다.')
        if kind=='python-cli' and spec.get('script'):
            if not inside(source,spec['script']).is_file():raise ValueError('원본 실행 파일이 없습니다.')
        elif kind in ('fastapi', 'python-cli'):
            if not python().is_file(): raise ValueError('먼저 setup을 실행하세요.')
            target = spec.get('app') or spec['entry']
            execute([python(), '-c', 'import importlib,sys,site;site.addsitedir(sys.argv.pop(1));getattr(importlib.import_module(sys.argv[1]),sys.argv[2])', str(source/'.platform-runtime/python'), *target.split(':')], work)
        print('실행 파일 확인 완료'); return
    if kind == 'node-http':
        execute([shutil.which('node') or 'node', inside(work, spec['entry']), *extra], work)
    elif kind == 'node-mcp':
        command = node_command(source, spec)
        if args.command == 'mcp-config':
            print(json.dumps({'mcpServers': {metadata['id']: {'command': command[0], 'args': command[1:], 'cwd': str(work)}}}, ensure_ascii=False, indent=2))
        else: execute(command, work)
    elif args.command == 'mcp-config': raise ValueError('MCP 앱이 아닙니다.')
    elif kind in ('static', 'vite'):
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(inside(work, spec.get('output', '.'))))
        print(f'http://127.0.0.1:{args.port}', flush=True)
        with http.server.ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server: server.serve_forever()
    elif kind == 'fastapi': execute([python(), '-m', 'uvicorn', '_platform_web:app', '--app-dir', ROOT, '--host', '127.0.0.1', '--port', str(args.port), *extra], work)
    elif kind=='python-cli' and spec.get('script'):
        execute([python() if python().is_file() else sys.executable,'-I','-X','utf8','-c','import runpy,sys,site;site.addsitedir(sys.argv.pop(1));sys.path.insert(0,sys.argv.pop(1));p=sys.argv.pop(1);sys.argv[0]=p;runpy.run_path(p,run_name="__main__")',str(source/'.platform-runtime/python'),source,inside(source,spec['script']),*extra],work)
    elif kind == 'python-cli':
        execute([python(), '-c', 'import sys,site,importlib;site.addsitedir(sys.argv.pop(1));m,n=sys.argv.pop(1).split(":");sys.exit(getattr(importlib.import_module(m),n)())', str(source/'.platform-runtime/python'),spec['entry'], *extra], work)
    elif kind=='powershell':
        if os.name!='nt':raise ValueError('Windows 전용 설치 프로그램은 macOS에서 실행할 수 없습니다.')
        executable=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
        script=inside(source,spec['script'])
        if not executable.is_file():raise ValueError('Windows PowerShell이 필요합니다.')
        execute([executable,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',script,*extra],work)
    else: raise ValueError('독립 실행을 지원하지 않는 유형입니다.')


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc: sys.exit(str(exc))
