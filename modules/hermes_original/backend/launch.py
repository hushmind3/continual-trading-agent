"""Launch the untouched checkout through its official PM environment."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'runtime/ai_agent/HermesOriginal'
SOURCE = BASE / 'source'
HOME = BASE / 'home'


def environment():
    env = {k: v for k, v in os.environ.items() if not k.startswith('HERMES_')}
    env.pop('PYTHONPATH', None)
    env.pop('VIRTUAL_ENV', None)
    env.update(HERMES_HOME=str(HOME), HERMES_RUNTIME_DIR=str(BASE / 'tools'))
    return env


def launch(arguments):
    env = environment()
    result = subprocess.run([sys.executable, '-m', 'pm.cli', 'env'], cwd=SOURCE,
                            env=env, capture_output=True, text=True, check=True)
    managed = json.loads(result.stdout)
    # `pm env` returns contributions only; retain the OS shell/system tools.
    managed['PATH'] = os.pathsep.join((managed['PATH'], env.get('PATH', os.defpath)))
    env.update(managed)
    # PM owns the interpreter and every dependency; no copied engine or bootstrap patches.
    import shutil
    python = shutil.which('python3', path=env['PATH'])
    if not python:
        raise RuntimeError('원본 PM의 Python 환경이 준비되지 않았습니다.')
    ready = os.environ.get('HERMES_DESKTOP_READY_FILE')
    if ready:
        env['HERMES_DESKTOP_READY_FILE'] = ready
    os.chdir(SOURCE)
    os.execve(python, [python, str(SOURCE / 'hermes'), *arguments], env)


if __name__ == '__main__':
    launch(sys.argv[1:])
