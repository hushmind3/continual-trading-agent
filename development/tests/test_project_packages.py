"""Independent execution, reinstall, removal, and isolated dependency ownership."""
import base64
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import adapters, installer, lifecycle, localization, package_import, packages, python_packages, runtime, store


class PackageTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / 'runtime/projects/manage/verification'; base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base); self.root = Path(self.temp.name)
        self.state = self.root / 'runtime/projects/manage'
        self.patches = [patch.object(store, 'ROOT', self.root), patch.object(store, 'STATE', self.state),
            patch.object(installer, 'ROOT', self.root), patch.object(installer, 'STATE', self.state),
            patch.object(installer, 'RESTARTING', False), patch.object(installer, 'JOBS', {}),
            patch.dict(sys.modules, {'menu_registry': SimpleNamespace(MODULE_ENTRIES=[])})]
        for item in self.patches: item.start()

    def tearDown(self):
        for item in reversed(self.patches): item.stop()
        self.temp.cleanup()

    def project(self):
        source = self.state / 'projects/p_example/versions/v1/source'; source.mkdir(parents=True)
        (source / 'index.html').write_text('<!doctype html><h1>portable original app</h1>', encoding='utf8')
        record = {'id': 'p_example', 'repository': 'sample/example', 'url': 'https://github.com/sample/example',
            'title': 'Example', 'stage': 'ready', 'active_source': str(source),
            'environment': {'API_KEY': 'private_value_987'}, 'adapter': {'kind': 'static', 'directory': '.', 'output': '.'}}
        store.save(record); return record, source

    def test_export_runs_outside_platform_and_reinstalls_without_ai_or_download(self):
        record, source = self.project()
        (source / '.env').write_text('PRIVATE=private_value_987')
        (source / '.platform-runtime').mkdir(); (source / '.platform-runtime/cache').write_text('cache')
        result = packages.export(record['id']); archive = source.parents[2] / 'exports' / result['filename']
        data = archive.read_bytes(); outside = self.root / 'standalone'; outside.mkdir()
        with zipfile.ZipFile(io.BytesIO(data)) as bundle:
            self.assertNotIn('source/.env', bundle.namelist())
            self.assertFalse(any('.platform-runtime' in name for name in bundle.namelist()))
            self.assertNotIn('private_value_987', bundle.read('app-package.json').decode())
            bundle.extractall(outside)
        # Delete all original installation files. The extracted app must still run.
        lifecycle.remove(record['id'])
        checked = subprocess.run([sys.executable, '-I', str(outside / 'run.py'), 'check'], cwd=outside, capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        with socket.socket() as socket_:
            socket_.bind(('127.0.0.1', 0)); port = socket_.getsockname()[1]
        process = subprocess.Popen([sys.executable, '-I', str(outside / 'run.py'), 'run', '--port', str(port)],
            cwd=outside, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 8
            while True:
                try:
                    with urlopen(f'http://127.0.0.1:{port}/', timeout=1) as response: content = response.read()
                    break
                except OSError:
                    if time.monotonic() > deadline: raise
                    time.sleep(.1)
            self.assertIn(b'portable original app', content)
        finally: process.terminate(); process.wait(timeout=5)
        with patch.object(installer, 'run_command') as command, patch.object(runtime, 'verify_ui', return_value=True), \
             patch.object(adapters, 'generate_with_hermes', side_effect=AssertionError('User model must not be used')) as model:
            imported = package_import.install(base64.b64encode(data).decode())
            deadline = time.monotonic() + 8
            while installer.JOBS and time.monotonic() < deadline: time.sleep(.05)
        model.assert_not_called()
        self.assertFalse(any('clone' in call.args[0] for call in command.call_args_list))
        installed = store.read(imported['id'])
        self.assertEqual(installed['stage'], 'awaiting_activation', installed.get('error'))
        self.assertTrue((Path(installed['active_source']) / 'index.html').is_file())
        self.assertFalse(list((self.state / 'imports').iterdir()))

    def test_invalid_archives_cannot_write_outside_staging(self):
        for name in ('../escaped.txt', 'source/../../escaped.txt', 'source/C:escaped', 'source/CON', 'source/./index.html'):
            data = io.BytesIO()
            with zipfile.ZipFile(data, 'w') as archive: archive.writestr(name, 'unexpected')
            with self.assertRaises(ValueError): package_import.install(base64.b64encode(data.getvalue()).decode())
        self.assertFalse((self.state / 'escaped.txt').exists())

    def test_unsupported_install_does_not_automatically_load_a_model(self):
        source = self.root / 'unknown'; source.mkdir(); (source / 'README.md').write_text('No entry point')
        record = {'id': 'p_unknown', 'url': 'https://github.com/sample/unknown', 'title': 'Unknown'}
        with patch.object(adapters, 'generate_with_hermes') as model:
            installer.install(record, threading.Event(), source)
        model.assert_not_called(); self.assertEqual(store.read('p_unknown')['stage'], 'needs_adapter')

    def test_python_dependencies_are_removable_and_do_not_change_shared_interpreter(self):
        record, source = self.project()
        wheel = self.root / 'owned_dependency_probe-1.0-py3-none-any.whl'
        with zipfile.ZipFile(wheel, 'w') as archive:
            archive.writestr('owned_dependency_probe/__init__.py', 'def main():\n print("private dependency works")\n')
            archive.writestr('owned_dependency_probe-1.0.dist-info/METADATA', 'Metadata-Version: 2.1\nName: owned-dependency-probe\nVersion: 1.0\n')
            archive.writestr('owned_dependency_probe-1.0.dist-info/WHEEL', 'Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
            archive.writestr('owned_dependency_probe-1.0.dist-info/RECORD', '')
        (source / 'requirements.txt').write_text(str(wheel), encoding='utf8')
        spec = {'kind': 'python-cli', 'directory': '.', 'entry': 'owned_dependency_probe:main'}
        def run(command, folder, timeout):
            subprocess.run(command, cwd=folder, check=True, capture_output=True, timeout=timeout,
                           env={**os.environ, 'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'})
        python_packages.prepare(source, spec, run)
        self.assertIsNone(importlib.util.find_spec('owned_dependency_probe'))
        result = runtime.run_cli({**record, 'adapter': spec}, [])
        self.assertIn('private dependency works', result['text'])
        (source / 'app.py').write_text('from fastapi import FastAPI\nimport owned_dependency_probe\napp=FastAPI()\n', encoding='utf8')
        runtime.verify(source, {'kind': 'fastapi', 'directory': '.', 'app': 'app:app'})
        lifecycle.remove(record['id'])
        self.assertFalse(source.exists()); self.assertIsNone(importlib.util.find_spec('owned_dependency_probe'))

    def test_translation_does_not_load_a_model(self):
        from unittest.mock import Mock
        bridge = Mock(); bridge.call.return_value = {'local_model': {'state': 'idle'}}
        with patch.dict(sys.modules, {'ai_agent.choki.engine.bridge': SimpleNamespace(bridge=bridge)}):
            localization.translate(['English description'], 'test-no-model')
        bridge.call.assert_called_once_with('status')
        self.assertIn('자동으로 불러오지', localization.ERRORS.pop('test-no-model')[1])

    def test_git_ignored_module_changes_require_api_and_frontend_application(self):
        sys.path.insert(0, str(ROOT / 'development/scripts'))
        import start_server
        def git(command, **kwargs): return b'' if 'ls-files' in command else 'revision'
        with patch.object(start_server, 'ROOT', self.root), patch.object(start_server.subprocess, 'check_output', side_effect=git), \
             patch.object(Path, 'home', return_value=self.root):
            before, _ = start_server.sources()
            module = self.root / 'modules/external_ignored'; module.mkdir(parents=True)
            (module / 'module.json').write_text('{"id":"external_ignored"}')
            after, _ = start_server.sources()
        self.assertNotEqual(before['frontend'], after['frontend'])
        self.assertNotEqual(before['backend'], after['backend'])


if __name__ == '__main__': unittest.main()
