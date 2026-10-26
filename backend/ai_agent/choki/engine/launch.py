"""Start the existing platform worker with the official PM-owned Python/env."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    engine = Path(__file__).resolve().parent
    root = next(parent for parent in engine.parents if (parent/'backend/platform_modules.py').is_file())
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.pop('VIRTUAL_ENV', None)
    env['HERMES_RUNTIME_DIR'] = str(root / 'runtime/shared/engines/hermes-pm')
    result = subprocess.run([sys.executable, '-m', 'pm.cli', 'env'], cwd=engine/'upstream',
                            env=env, capture_output=True, text=True, encoding='utf-8', check=True)
    managed = json.loads(result.stdout)
    managed['PATH'] = os.pathsep.join((managed.get('PATH',''), env.get('PATH',os.defpath)))
    env.update(managed)
    python = shutil.which('python.exe' if os.name == 'nt' else 'python3', path=env['PATH'])
    if not python:
        raise RuntimeError('공식 패키지 관리자의 Python 실행 환경이 없습니다.')
    command = [python, '-I', '-X', 'utf8', '-B', str(engine/'worker.py')]
    if os.name == 'nt':
        raise SystemExit(subprocess.call(command, cwd=root, env=env))
    os.execve(python, command, env)


if __name__ == '__main__':
    main()
