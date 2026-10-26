"""Launch the official PM environment with the requested Korean dashboard patch."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'runtime/ai_agent/HermesOriginal'
SOURCE = BASE / 'source'
HOME = BASE / 'home'
KOREAN_PATCH_BASE = 'bf0203a794a07aac3ff764972ab9087baa4e4f4e'


def environment():
    env = {k: v for k, v in os.environ.items() if not k.startswith('HERMES_')}
    env.pop('PYTHONPATH', None)
    env.pop('VIRTUAL_ENV', None)
    env.update(HERMES_HOME=str(HOME), HERMES_RUNTIME_DIR=str(ROOT / 'runtime/shared/engines/hermes-pm'))
    return env


def launch(arguments):
    if os.name == 'nt':
        patch = Path(__file__).resolve().parent / 'patches' / 'windows-local-runtime.patch'
        applied = subprocess.run(['git', 'apply', '--reverse', '--check', '--ignore-space-change', str(patch)],
                                 cwd=SOURCE, capture_output=True)
        if applied.returncode:
            subprocess.run(['git', 'apply', '--check', '--ignore-space-change', str(patch)], cwd=SOURCE, check=True)
            subprocess.run(['git', 'apply', '--ignore-space-change', str(patch)], cwd=SOURCE, check=True)
    if arguments and arguments[0] == 'dashboard':
        patch = Path(__file__).resolve().parent / 'patches' / 'korean-ui.patch'
        # Reuse the already-applied patch; never overwrite upstream/local conflicts.
        applied = subprocess.run(['git', 'apply', '--reverse', '--check', '--ignore-space-change', str(patch)],
                                 cwd=SOURCE, capture_output=True)
        if applied.returncode:
            revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE,
                                               text=True).strip()
            if revision == KOREAN_PATCH_BASE:
                subprocess.run(['git', 'apply', '--check', '--ignore-space-change', str(patch)], cwd=SOURCE, check=True)
                subprocess.run(['git', 'apply', '--ignore-space-change', str(patch)], cwd=SOURCE, check=True)
            else:
                print('현재 원본은 보관된 한국어 패치의 기준 버전과 다릅니다. '
                      '패치를 적용하지 않고 공식 원본을 실행합니다.', file=sys.stderr, flush=True)
    env = environment()
    result = subprocess.run([sys.executable, '-m', 'pm.cli', 'env'], cwd=SOURCE,
                            env=env, capture_output=True, text=True, check=True)
    managed = json.loads(result.stdout)
    # `pm env` returns contributions only; retain the OS shell/system tools.
    managed['PATH'] = os.pathsep.join((managed['PATH'], env.get('PATH', os.defpath)))
    env.update(managed)
    # PM owns the interpreter and every dependency; no copied engine or bootstrap patches.
    import shutil
    python = shutil.which('python.exe' if os.name == 'nt' else 'python3', path=env['PATH'])
    if not python:
        raise RuntimeError('원본 PM의 Python 환경이 준비되지 않았습니다.')
    ready = os.environ.get('HERMES_DESKTOP_READY_FILE')
    if ready:
        env['HERMES_DESKTOP_READY_FILE'] = ready
    os.chdir(SOURCE)
    if os.name == 'nt':
        raise SystemExit(subprocess.call([python, str(SOURCE / 'hermes'), *arguments], env=env))
    os.execve(python, [python, str(SOURCE / 'hermes'), *arguments], env)


if __name__ == '__main__':
    launch(sys.argv[1:])
