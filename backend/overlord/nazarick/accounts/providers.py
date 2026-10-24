"""Browser definitions are owned by the module manifest, not the settings UI."""
import json
import os
from pathlib import Path
import shutil
import sys
import subprocess
import plistlib
from platform_modules import ROOT


def definitions():
    return json.loads((ROOT / 'modules/nazarick/module.json').read_text())['browser_providers']


def accounts():
    return json.loads((ROOT / 'modules/nazarick/module.json').read_text())['account_providers']


def executable(spec):
    candidates = []
    if sys.platform == 'darwin' and spec.get('macos'):
        candidates = [base / spec['macos'] for base in (Path('/Applications'), Path.home() / 'Applications')]
        if not any(path.is_file() for path in candidates) and spec.get('bundle_id'):
            # Finder permits renamed apps, e.g. Brave Browser 2.app. Resolve by vendor bundle ID.
            found = subprocess.run(['/usr/bin/mdfind', 'kMDItemCFBundleIdentifier == "' + spec['bundle_id'] + '"'],
                                   capture_output=True, text=True, timeout=3, check=False)
            for line in found.stdout.splitlines():
                app = Path(line)
                try:
                    metadata = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
                    if metadata.get('CFBundleIdentifier') == spec['bundle_id']:
                        candidates.append(app / 'Contents/MacOS' / metadata['CFBundleExecutable'])
                except (OSError, ValueError, KeyError):
                    pass
    elif os.name == 'nt' and spec.get('windows'):
        candidates = [Path(os.environ[key]) / spec['windows'] for key in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA') if os.environ.get(key)]
    elif sys.platform != 'darwin' and os.name != 'nt':
        candidates = [Path(found) for name in spec.get('linux', []) if (found := shutil.which(name))]
    return next((path for path in candidates if path.is_file()), None)


def catalog():
    return [{'id': item['id'], 'name': item['name'], 'automation': item['engine'] == 'chromium',
             'installed': executable(item) is not None} for item in definitions()]


def get(key, require_installed=True):
    item = next((item for item in definitions() if item['id'] == key), None)
    if not item or require_installed and executable(item) is None:
        raise ValueError('설치된 브라우저를 선택하세요.')
    return item
