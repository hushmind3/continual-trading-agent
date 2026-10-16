"""Project-owned Python packages; the shared interpreter is never modified."""
from pathlib import Path
import json
import sys
from .store import owned


def folder(source):
    return owned(source, '.platform-runtime/python')


def prepare(source, spec, run):
    work = owned(source, spec.get('directory', '.'))
    requirements = next((path for path in (work / 'requirements.txt', source / 'requirements.txt') if path.is_file()), None)
    if spec['kind'] == 'native':
        metadata = json.loads((source / 'module.json').read_text(encoding='utf8'))
        if metadata.get('requirements'): requirements = owned(source, metadata['requirements'])
        if not requirements: return
        # Native routers run in the host. Do not change that interpreter as a side effect of installing an app.
        report = source.parent / 'native-dependencies.json'
        try:
            run([sys.executable, '-m', 'pip', 'install', '--dry-run', '--report', str(report), '-r', str(requirements)], work, 900)
            if json.loads(report.read_text(encoding='utf8')).get('install'):
                raise ValueError('이 플랫폼 모듈은 공용 Python에 없는 의존성이 필요합니다. 공용 환경을 변경하지 않고 설치를 중단했습니다.')
        finally:
            report.unlink(missing_ok=True)
        return
    target = folder(source)
    target.mkdir(parents=True, exist_ok=True)
    base = [sys.executable, '-m', 'pip', 'install', '--target', str(target), '--upgrade', '--no-warn-script-location']
    if requirements: run([*base, '-r', str(requirements)], work, 900)
    project = work / 'pyproject.toml'
    if (spec['kind'] == 'python-cli' and spec.get('install')) or (project.is_file() and not requirements):
        run([*base, str(work)], work, 900)


def cli_command(source, spec, arguments):
    script = ('import sys,site,importlib; p=sys.argv.pop(1);site.addsitedir(p);sys.path.insert(0,p);'
              'sys.path.insert(0,sys.argv.pop(1));m,n=sys.argv.pop(1).split(":");'
              'sys.exit(getattr(importlib.import_module(m),n)())')
    return [sys.executable, '-I', '-X', 'utf8', '-B', '-c', script, str(folder(source)),
            str(owned(source, spec.get('directory', '.'))), spec['entry'], *arguments]
