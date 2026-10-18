"""Installer contracts, real ASGI IPC/UI execution, and failed-update rollback."""
import base64
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import adapters, github, installer, runtime, store


class InstallerTests(unittest.TestCase):



    def test_search_returns_more_pages_and_passes_sort(self):
        with patch.object(github, 'github', return_value={'total_count': 89, 'items': []}) as fetch:
            result = github.search('rea', 2, 'stars')
        self.assertTrue(result['has_more'])
        self.assertIn('per_page=30', fetch.call_args.args[0])
        self.assertIn('page=2', fetch.call_args.args[0])
        self.assertIn('sort=stars', fetch.call_args.args[0])
        self.assertEqual(github.repository('https://github.com/morluto/rea.git'), 'morluto/rea')

    def test_agent_model_preparation_waits_for_ready(self):
        from platform_plugins.projects.agent_setup import ensure_ready
        bridge = Mock()
        bridge.call.side_effect = [
            {'job': {'state': 'idle'}, 'local_model': {'state': 'idle'}},
            {'local_model': 'C:/models/chosen.gguf'}, {},
            {'local_model': {'state': 'ready'}}]
        ensure_ready(bridge, threading.Event(), Mock())
        self.assertIn(unittest.mock.call('model/load', {'path': 'C:/models/chosen.gguf'}), bridge.call.call_args_list)

    def test_agent_model_preparation_leaves_active_work_alone(self):
        from platform_plugins.projects.agent_setup import ensure_ready
        bridge = Mock(); bridge.call.return_value = {'job': {'state': 'running'}}
        with self.assertRaisesRegex(ValueError, '다른 작업'):
            ensure_ready(bridge, threading.Event(), Mock())
        bridge.call.assert_called_once_with('status')

    def test_node_mcp_detects_repository_manifest_before_website(self):
        (self.source / 'server.json').write_text(json.dumps({'repository': {'url': 'https://github.com/morluto/rea'},
            'packages': [{'registryType': 'npm', 'identifier': 'rea-agents', 'version': '6.5.0',
                'transport': {'type': 'stdio'}, 'packageArguments': [{'type': 'positional', 'value': 'mcp'}]}]}))
        (self.source / 'package.json').write_text(json.dumps({'name': 'rea-agents', 'version': '6.5.0', 'bin': {'rea': 'scripts/rea.mjs'}}))
        website = self.source / 'website'; website.mkdir(); (website / 'index.html').write_text('Marketing website')
        spec = adapters.detect(self.source)
        self.assertEqual(spec['kind'], 'node-mcp')
        self.assertEqual(spec['arguments'], ['mcp'])
        with self.assertRaises(ValueError): adapters.validate(self.source, {**spec, 'script': '../outside.js'})

    def test_wpf_is_reported_as_missing_native_adapter(self):
        from platform_plugins.projects.requirements import check, RequirementError
        (self.source / 'app.sln').write_text('Project("guid") = "App", "App/App.csproj", "guid"')
        (self.source / 'App').mkdir(); (self.source / 'App/App.csproj').write_text('<OutputType>WinExe</OutputType>')
        with self.assertRaisesRegex(RequirementError, '.NET 데스크톱'): check(self.source)

    def setUp(self):
        verification = ROOT / 'runtime/projects/manage/verification'
        verification.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=verification)
        self.base = Path(self.temp.name); self.source = self.base / 'version/source'; self.source.mkdir(parents=True)

    def tearDown(self):
        runtime.close(); self.temp.cleanup()

    def test_repository_is_public_github_only(self):
        self.assertEqual(github.repository('https://github.com/mdn/beginner-html-site-styled.git'), 'mdn/beginner-html-site-styled')
        for value in ('https://evil.test/a/b', '--upload-pack=evil', '../x', 'https://github.com/u/r/tree/main', 'https://user:secret@github.com/u/r'):
            with self.subTest(value=value), self.assertRaises(ValueError): github.repository(value)

    def test_vite_and_fastapi_are_detected_together(self):
        ui = self.source / 'frontend'; ui.mkdir()
        (ui / 'package.json').write_text(json.dumps({'devDependencies': {'vite': '*'}, 'scripts': {'build': 'vite build'}}))
        backend = self.source / 'backend'; backend.mkdir()
        (backend / 'main.py').write_text('from fastapi import FastAPI\napp=FastAPI()\n')
        spec = adapters.detect(self.source)
        self.assertEqual((spec['kind'], spec['app'], spec['ui']['kind']), ('fastapi', 'main:app', 'vite'))

    def test_server_rendered_home_precedes_stale_docs_and_keeps_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        docs = self.source / 'docs'; docs.mkdir(); (docs/'index.html').write_text('Old demo')
        (self.source/'server.py').write_text('from fastapi import FastAPI,Header,HTTPException\nfrom fastapi.responses import HTMLResponse\napp=FastAPI()\n'
            '@app.get("/",response_class=HTMLResponse)\ndef home(): return "<html><head></head><body>Live company <a href=\'/product\'>Product</a></body></html>"\n'
            '@app.get("/private")\ndef private(x_owner: str=Header("")):\n if x_owner!="owner": raise HTTPException(401)\n return {"current":True}\n')
        spec=adapters.detect(self.source)
        self.assertEqual((spec['kind'],spec['app'],spec['ui']['kind']),('fastapi','server:app','asgi'))
        runtime.verify(self.source,spec)
        state=self.base/'state'
        with patch.object(store,'STATE',state):
            store.save({'id':'p_server','adapter':spec,'active_source':str(self.source)})
            app=FastAPI(); runtime.register_host(app)
            with TestClient(app) as client:
                response=client.get('/assets/projects/p_server/index.html')
                self.assertEqual(response.status_code,200); self.assertIn('Live company',response.text)
                self.assertIn('/assets/projects/p_server/product',response.text)
                self.assertEqual(response.headers['cache-control'],'no-store')
                self.assertEqual(client.get('/assets/projects/p_server/private').status_code,401)
                self.assertTrue(client.get('/assets/projects/p_server/private',headers={'X-Owner':'owner'}).json()['current'])
        log=self.base/'server-ui.log'
        self.assertTrue(runtime.verify_ui(self.source,spec,{},lambda cmd,folder,timeout:installer.run_command(cmd,folder,log,threading.Event(),timeout)))

    def test_existing_app_update_uses_same_module_without_host_build(self):
        root=self.base/'host'; state=root/'runtime/projects/manage'
        module=root/'modules/external_p_demo'; module.mkdir(parents=True)
        original=json.dumps({'id':'external_p_demo','install_revision':'first'})
        (module/'module.json').write_text(original)
        old=state/'projects/demo/versions/previous/source'; (old/'data').mkdir(parents=True)
        (old/'data/keep.txt').write_text('user data')
        (old/'data/.gitkeep').write_text('tracked placeholder')
        subprocess.run(['git','init','-q',str(old)],check=True)
        subprocess.run(['git','-C',str(old),'add','data/.gitkeep'],check=True)
        (self.source/'index.html').write_text('<html><body>NEW APP</body></html>')
        record={'id':'p_demo','folder_name':'demo','title':'demo','module_id':'external_p_demo','active_source':str(old),'url':'https://github.com/owner/demo'}
        with patch.object(installer,'ROOT',root),patch.object(installer,'STATE',state),patch.object(store,'STATE',state),patch.object(store,'ROOT',root), \
             patch.object(runtime,'verify_ui',return_value=True),patch.object(installer,'run_command') as command:
            installer.install(record,threading.Event(),self.source)
            command.assert_not_called()
            result=store.read('p_demo'); self.assertEqual(result['stage'],'ready')
            self.assertEqual((module/'module.json').read_text(),original)
            source=Path(result['active_source'])
            self.assertEqual(source.parent.name,'version-1')
            self.assertIn('NEW APP',(source/'index.html').read_text())
            self.assertEqual((source/'data/keep.txt').read_text(),'user data')

    def test_asgi_worker_preserves_state_and_actual_working_directory(self):
        (self.source / 'main.py').write_text('from fastapi import FastAPI\nimport os\napp=FastAPI()\ncounter=0\n'
            '@app.get("/counter")\ndef count():\n global counter\n counter+=1\n return {"count":counter,"cwd":os.getcwd()}\n')
        spec = adapters.detect(self.source); runtime.verify(self.source, spec)
        record = {'id': 'p_test', 'active_source': str(self.source), 'adapter': spec}
        for count in (1, 2):
            response = runtime.invoke(record, {'path': '/counter', 'method': 'GET'})
            self.assertEqual(response['status'], 200)
            data = json.loads(base64.b64decode(response['body']))
            self.assertEqual(data['count'], count); self.assertEqual(Path(data['cwd']), self.source)

    def test_ui_verifier_rejects_javascript_failures(self):
        (self.source / 'index.html').write_text('<html><head></head><body>Working project</body></html>')
        spec = adapters.detect(self.source)
        log = self.base / 'verification.log'
        def run(command, folder, timeout): installer.run_command(command, folder, log, threading.Event(), timeout)
        self.assertTrue(runtime.verify_ui(self.source, spec, {}, run))
        (self.source / 'index.html').write_text('<html><head></head><body><script>throw Error("ACTUAL_UI_FAILURE")</script></body></html>')
        with self.assertRaisesRegex(ValueError, 'ACTUAL_UI_FAILURE'):
            runtime.verify_ui(self.source, spec, {}, run)

    def test_original_ui_fetch_uses_single_api_gateway(self):
        (self.source / 'main.py').write_text('from fastapi import FastAPI\napp=FastAPI()\n@app.get("/result")\ndef result(): return {"connected":True}\n')
        ui = self.source / 'frontend'; ui.mkdir()
        (ui / 'index.html').write_text('<html><head></head><body>Loading<script>'
            'fetch("/result").then(r=>r.json()).then(data=>{if(!data.connected)throw Error("API_BRIDGE_FAILED");document.body.textContent="Connected"})'
            '</script></body></html>')
        spec = adapters.detect(self.source); log = self.base / 'connected-ui.log'
        def run(command, folder, timeout): installer.run_command(command, folder, log, threading.Event(), timeout)
        self.assertTrue(runtime.verify_ui(self.source, spec, {}, run))

    def test_root_absolute_asset_is_not_falsely_verified_at_platform_mount(self):
        (self.source / 'index.html').write_text('<html><head><script src="/code.js"></script></head><body>App</body></html>')
        (self.source / 'code.js').write_text('console.log("asset")')
        log = self.base / 'mount.log'
        def run(command, folder, timeout): installer.run_command(command, folder, log, threading.Event(), timeout)
        with self.assertRaisesRegex(ValueError, '플랫폼 밖의 경로'):
            runtime.verify_ui(self.source, adapters.detect(self.source), {}, run)

    def test_cookie_auth_requires_adapter_instead_of_false_ready(self):
        (self.source / 'main.py').write_text('from fastapi import FastAPI,Security\nfrom fastapi.security import APIKeyCookie\n'
            'app=FastAPI()\ncookie=APIKeyCookie(name="session")\n@app.get("/")\ndef home(token=Security(cookie)):return {"ok":True}\n')
        with self.assertRaisesRegex(ValueError, '인증 어댑터'):
            runtime.verify(self.source, adapters.detect(self.source))

    def test_failed_update_restores_existing_program_and_record(self):
        root = self.base / 'host'; (root / 'modules/demo').mkdir(parents=True)
        (root / 'modules/demo/old.txt').write_text('keep this program')
        source = self.base / 'native'; (source / 'backend').mkdir(parents=True); (source / 'frontend').mkdir()
        (source / 'module.json').write_text(json.dumps({'schema': 1, 'id': 'demo', 'group': {'id': 'demo', 'title': 'Demo'},
            'backend': {'namespace': 'demo', 'entry': 'register'}, 'frontend': {'entry': 'frontend/register.ts'}}))
        record = {'id': 'p_demo', 'module_id': 'demo', 'title': 'demo', 'repository': 'owner/demo',
            'url': 'https://github.com/owner/demo', 'active_source': 'previous-source', 'environment': {}}
        state = root / 'runtime/projects/manage'
        with patch.object(installer, 'ROOT', root), patch.object(installer, 'STATE', state), patch.object(store, 'STATE', state), \
             patch.object(installer, 'run_command', side_effect=ValueError('deliberate import failure')):
            installer.install(record, threading.Event(), source)
            restored = store.read('p_demo')
            self.assertEqual(restored['stage'], 'failed'); self.assertEqual(restored['active_source'], 'previous-source')
            self.assertEqual((root / 'modules/demo/old.txt').read_text(), 'keep this program')
            self.assertTrue(list((root / '휴지통/modules').glob('demo-*')))

    def test_adapter_cannot_escape_owned_project(self):
        with self.assertRaises(ValueError): adapters.validate(self.source, {'kind': 'static', 'directory': '../..'})
        value = installer.public({'environment': {'API_KEY': 'secret-value'}, 'error': 'failed secret-value'})
        self.assertNotIn('secret-value', value['error']); self.assertNotIn('environment', value)

    def test_record_replace_retries_windows_sharing_violation(self):
        import os
        original = os.replace; attempts = []
        def replace(source, target):
            attempts.append(1)
            if len(attempts) == 1: raise PermissionError('Windows sharing violation')
            return original(source, target)
        with patch.object(store, 'STATE', self.base / 'state'), patch.object(store.os, 'replace', side_effect=replace):
            store.save({'id': 'p_retry', 'stage': 'download'})
            self.assertEqual(store.read('p_retry')['stage'], 'download')
            self.assertEqual(len(attempts), 2)

    def test_update_is_not_ready_until_its_revision_is_loaded(self):
        from types import SimpleNamespace
        state = self.base / 'state'
        metadata = {'id': 'external_demo', 'install_revision': 'old'}
        with patch.object(store, 'STATE', state), patch.dict(sys.modules, {'menu_registry': SimpleNamespace(MODULE_ENTRIES=[(metadata, object())])}):
            store.save({'id': 'p_demo', 'module_id': 'external_demo', 'install_revision': 'new', 'stage': 'awaiting_activation'})
            self.assertEqual(installer.installed()[0]['stage'], 'awaiting_activation')
            metadata['install_revision'] = 'new'
            self.assertEqual(installer.installed()[0]['stage'], 'ready')


if __name__ == '__main__': unittest.main()
