"""Pinned original UI registration and uninstall visibility, without a user model."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import store, workspaces


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        verification = ROOT / 'runtime/projects/manage/verification'
        verification.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=verification)
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        root_patch=patch.object(store,'ROOT',self.state);root_patch.start();self.addCleanup(root_patch.stop)
        module=self.state/'modules/projects/demo';module.mkdir(parents=True)
        (module/'module.json').write_text(json.dumps({'id':'projects/demo'}),encoding='utf-8')
        self.patch = patch.object(store, 'STATE', self.state)
        self.patch.start(); self.addCleanup(self.patch.stop)
        source = self.state / 'projects/demo/source'; source.mkdir(parents=True)
        (source / 'ai_provider.py').write_text('async def compose(system,user): return "original"', encoding='utf-8')
        self.record = {'module_id':'projects/demo','id': 'p_demo', 'folder_name': 'demo', 'repository': 'owner/sample', 'stage': 'ready',
            'active_source': str(source), 'adapter': {'kind': 'fastapi'}}
        store.save(self.record)
        self.config = {'revision': 'a' * 40, 'path': 'templates/admin.html', 'navigation': 'data-tab',
            'tabs': [{'id': 'overview', 'title': '회사 현황'}, {'id': 'talk', 'title': 'AI 총괄 대화'}]}

    def connect(self):
        with patch.object(workspaces, 'urlopen', return_value=io.BytesIO(b'<html><body>original</body></html>')):
            workspaces.connect('p_demo', self.config)

    def test_installation_owns_document_and_connection(self):
        self.connect()
        record = store.read('p_demo')
        self.assertTrue(record['harness']['enabled'])
        self.assertEqual(record['workspace_ui']['url'], 'https://raw.githubusercontent.com/owner/sample/' + 'a' * 40 + '/templates/admin.html')
        self.assertEqual([t['title'] for t in workspaces.tabs()['items']], ['회사 현황', 'AI 총괄 대화'])
        self.assertIn('original', workspaces.document(record))

    def test_detached_and_removed_app_have_no_host_tabs(self):
        self.connect(); record = store.read('p_demo'); record['stage'] = 'removed'; store.save(record)
        self.assertEqual(workspaces.tabs(), {'items': []})
        (self.state / 'registry/p_demo.json').unlink()
        self.assertEqual(workspaces.tabs(), {'items': []})

    def test_opted_in_adapter_is_app_owned_and_disabled_with_its_harness(self):
        self.config['recipe']='company-v1';self.connect()
        record=store.read('p_demo')
        self.assertTrue(workspaces.tabs()['items'][0]['conversation'])
        self.assertEqual(workspaces.adapter(record),self.state/'projects/demo/integrations/hermes/workflow.py')
        self.config.pop('recipe');self.connect()
        self.assertEqual(store.read('p_demo')['workspace_ui']['recipe'],'company-v1')
        record['harness']['enabled']=False
        self.assertIsNone(workspaces.adapter(record))

    def test_mutated_document_is_rejected(self):
        self.connect(); record = store.read('p_demo')
        store.owned(store.project_folder(record), record['workspace_ui']['document']).write_text('modified', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '무결성'): workspaces.document(record)

    def test_unpinned_or_outside_path_does_not_download(self):
        for change in ({'revision': 'main'}, {'path': '../admin.html'}):
            with patch.object(workspaces, 'urlopen') as network, self.assertRaises(ValueError):
                workspaces.connect('p_demo', {**self.config, **change})
            network.assert_not_called()


if __name__ == '__main__': unittest.main()
