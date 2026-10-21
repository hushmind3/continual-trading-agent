"""Shared native executable discovery; no installs, shells or background probes."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


def native_runtime_path(value):
    """Resolve legacy manifest paths on this host without changing the manifest."""
    value = value.replace('\\', '/')
    if os.name != 'nt':
        if value.endswith('/Scripts/python.exe'):
            return value.removesuffix('/Scripts/python.exe') + '/bin/python'
        if value.endswith('/llama-server.exe'):
            return value.removesuffix('.exe')
    return value


def npm_command(node=None):
    node = node or shutil.which('node')
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not node or not npm:
        raise ValueError('Node.js와 npm 실행기를 찾지 못했습니다.')
    resolved = Path(npm).resolve()
    candidates = [resolved] if resolved.suffix == '.js' else []
    candidates += [Path(npm).parent / 'node_modules/npm/bin/npm-cli.js',
                   Path(node).resolve().parent.parent / 'lib/node_modules/npm/bin/npm-cli.js']
    cli = next((path for path in candidates if path.is_file()), None)
    if cli is None:
        raise ValueError('설치된 npm-cli.js를 찾지 못했습니다.')
    return [node, str(cli)]


def browser_executable(browser=None):
    if browser not in (None, 'chrome', 'edge'):
        raise ValueError('지원하는 브라우저를 선택하세요.')
    candidates = []
    if not browser and os.environ.get('AGENT_BROWSER_EXECUTABLE_PATH'):
        candidates.append(Path(os.environ['AGENT_BROWSER_EXECUTABLE_PATH']).expanduser())
    names = [browser] if browser else ['chrome', 'edge']
    if sys.platform == 'darwin':
        for name in names:
            app = 'Google Chrome' if name == 'chrome' else 'Microsoft Edge'
            candidates += [root / (app + '.app') / 'Contents/MacOS' / app
                           for root in (Path('/Applications'), Path.home() / 'Applications')]
    elif os.name == 'nt':
        for name in names:
            relative = 'Google/Chrome/Application/chrome.exe' if name == 'chrome' else 'Microsoft/Edge/Application/msedge.exe'
            candidates += [Path(os.environ[key]) / relative
                           for key in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA') if os.environ.get(key)]
    else:
        commands = ('google-chrome', 'chromium', 'chromium-browser') if browser != 'edge' else ('microsoft-edge',)
        candidates += [Path(found) for name in commands if (found := shutil.which(name))]
    return next((path for path in candidates if path.is_file()
                 and (os.name == 'nt' or path.suffix.lower() != '.exe' and os.access(path, os.X_OK))), None)


def open_folder(folder):
    folder = Path(folder).resolve()
    if not folder.is_dir():
        raise ValueError('열 폴더가 없습니다.')
    if os.name == 'nt':
        os.startfile(str(folder))
    else:
        command = '/usr/bin/open' if sys.platform == 'darwin' else shutil.which('xdg-open')
        if not command:
            raise ValueError('이 환경에서 폴더를 열 실행기를 찾지 못했습니다.')
        subprocess.Popen([command, str(folder)], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {'path': str(folder)}
