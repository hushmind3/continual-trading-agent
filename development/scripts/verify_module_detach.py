"""Exercise real folder removal/restoration through the running module watcher."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
BASE = 'http://127.0.0.1:8766'
REPORT = ROOT / 'runtime/platform/module-verification.json'


def api(operation, payload=None):
    if payload is None:
        request = BASE + '/api?' + urllib.parse.urlencode({'operation': operation})
    else:
        request = urllib.request.Request(BASE + '/api', data=json.dumps(
            {'operation': operation, 'payload': payload}).encode(),
            headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def digest(paths):
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths if path.is_file()}


def wait_registration(present, timeout=180):
    deadline = time.monotonic() + timeout
    last = ''
    while time.monotonic() < deadline:
        try:
            ids = {item['id'] for item in api('platform/modules')['items']}
            assert {'finance', 'rea'} <= ids, ids
            with urllib.request.urlopen(BASE, timeout=10) as response:
                html = response.read().decode()
            asset = re.search(r'src="(/assets/index-[^"]+\.js)"', html)
            assert asset, 'Missing frontend entry'
            with urllib.request.urlopen(BASE + asset[1], timeout=10) as response:
                bundle = response.read().decode()
            if ('hermes' in ids) == present and ('Hermes-' in bundle) == present:
                return sorted(ids)
        except Exception as exc:
            last = str(exc)
        time.sleep(2)
    raise TimeoutError(f'Module registration did not become {present}: {last}')


def main():
    program = ROOT / 'modules/hermes'
    parked = ROOT / 'runtime/platform/module-detach/hermes'
    assert program.is_dir() and not parked.exists(), 'Unexpected detach paths'
    assert parked.resolve().is_relative_to((ROOT / 'runtime/platform').resolve())
    central = [ROOT / name for name in (
        'backend/menu_registry.py', 'backend/platform_modules.py', 'backend/web_api.py',
        'frontend/src/shell/module_loader.ts', 'frontend/src/shell/menu_groups/menu_registry.ts')]
    before = digest(central)
    report = {'started_at': time.time(), 'status': 'running', 'checks': []}
    def record(name, result):
        report['checks'].append({'name': name, 'result': result})
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
        print(name + ': ' + str(result), flush=True)
    try:
        record('initial_registration', wait_registration(True))
        assert api('platform/modules/prepare-detach', {'id': 'hermes'})['ready']
        state = ROOT / 'runtime/ai_agent/Hermes'
        persistent = [state / name for name in ('platform-settings.json', 'config.yaml', 'state.db')]
        saved = digest(persistent)
        assert saved, 'No persistent state found to verify'
        parked.parent.mkdir(parents=True, exist_ok=True)
        program.rename(parked)
        record('removed_registration_and_frontend', wait_registration(False))
        try:
            api('ai_agent/Hermes/sessions')
        except urllib.error.HTTPError as exc:
            assert exc.code == 404, exc.code
        else:
            raise AssertionError('Removed Hermes API still accessible')
        record('removed_api_404', True)
        assert digest(persistent) == saved, 'Persistent state changed while detached'
        parked.rename(program)
        record('restored_registration_and_frontend', wait_registration(True))
        assert digest(persistent) == saved, 'Persistent state changed during restoration'
        record('persistent_files_unchanged', list(saved))
        sessions = api('ai_agent/Hermes/sessions')
        record('restored_sessions_api', type(sessions).__name__)
        assert digest(central) == before, 'Central source edited during detach test'
        record('central_source_edits', 0)
        report['status'] = 'passed'
    except BaseException as exc:
        report.update(status='failed', error=str(exc))
        raise
    finally:
        if parked.exists() and not program.exists():
            parked.rename(program)
            try:
                wait_registration(True)
            except Exception as exc:
                report['restore_error'] = str(exc)
        report['finished_at'] = time.time()
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
