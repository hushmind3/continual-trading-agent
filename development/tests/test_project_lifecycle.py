"""Project ownership, real detachment/reconnection, and automatic agent registration."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import lifecycle, store, installer, runtime, agent_tasks, adapters


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / 'runtime/projects/manage/verification'; base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base); self.root = Path(self.temp.name)
        self.state = self.root / 'runtime/projects/manage'
        self.patches = [patch.object(store, 'ROOT', self.root), patch.object(store, 'STATE', self.state),
            patch.object(installer, 'ROOT', self.root), patch.object(installer, 'STATE', self.state),
            patch.object(installer, 'RESTARTING', False), patch.object(installer, 'JOBS', {}),
            patch.object(runtime, 'busy_reason', return_value=''),
            patch.dict(sys.modules, {'menu_registry': SimpleNamespace(MODULE_ENTRIES=[])})]
        for item in self.patches: item.start()

    def tearDown(self):
        for item in reversed(self.patches): item.stop()
        self.temp.cleanup()

    def project(self, key='p_example'):
        source = self.state / 'projects' / key / 'versions/v1/source'; source.mkdir(parents=True)
        (source / 'original.txt').write_text('original program')
        module = self.root / 'modules' / ('external_' + key); module.mkdir(parents=True)
        (module / 'module.json').write_text(json.dumps({'id': 'external_' + key, 'install_revision': 'v1'}))
        (module / 'program.py').write_text('working module')
        record = {'id': key, 'repository': 'sample/example', 'stage': 'ready', 'module_id': 'external_' + key,
            'install_revision': 'v1', 'active_source': str(source), 'adapter': {'kind': 'static'}}
        store.save(record); return record, source, module

    def test_detach_reconnect_preserves_files_without_install_or_ai(self):
        record, source, module = self.project()
        lifecycle.detach(record['id'])
        self.assertFalse(module.exists()); self.assertTrue(source.exists())
        self.assertEqual(store.read(record['id'])['stage'], 'removed')
        with patch.object(installer, 'start') as download:
            result = lifecycle.reconnect(record['id'])
        download.assert_not_called()
        self.assertEqual(result['stage'], 'awaiting_activation')
        self.assertEqual((module / 'program.py').read_text(), 'working module')
        self.assertEqual((source / 'original.txt').read_text(), 'original program')

    def test_readable_folder_migration_preserves_data_and_remove_ownership(self):
        record,source,module=self.project()
        record['install_log']=str(source.parent/'install.log')
        manifest=module/'module.json'; metadata=json.loads(manifest.read_text())
        metadata['data']=['runtime/projects/manage/projects/'+record['id']];manifest.write_text(json.dumps(metadata))
        store.assign_folder(record)
        self.assertEqual(record['folder_name'],'example')
        self.assertEqual((store.project_folder(record)/'versions/v1/source/original.txt').read_text(),'original program')
        self.assertFalse(source.exists()); self.assertIn('projects/example/',Path(record['active_source']).as_posix())
        self.assertEqual(json.loads(manifest.read_text())['data'],['runtime/projects/manage/projects/example'])
        lifecycle.detach(record['id']); lifecycle.reconnect(record['id']); lifecycle.remove(record['id'])
        self.assertFalse(store.project_folder(record).exists())

    def test_windows_directory_rename_failure_copies_before_removing_history(self):
        record,source,module=self.project(); previous=store.project_folder(record)
        rename=Path.rename
        def locked(path,target):
            if path==previous: raise PermissionError('Windows directory rename denied')
            return rename(path,target)
        with patch.object(Path,'rename',locked): store.assign_folder(record)
        self.assertFalse(previous.exists())
        self.assertEqual((Path(record['active_source'])/'original.txt').read_text(),'original program')
        self.assertEqual(store.read(record['id'])['folder_name'],'example')

    def test_permanent_remove_also_works_for_detached_projects(self):
        record, source, module = self.project()
        other, other_source, other_module = self.project('p_unrelated')
        lifecycle.detach(record['id'])
        result = lifecycle.remove(record['id'])
        self.assertTrue(result['permanent'])
        self.assertFalse((self.state / 'projects' / record['id']).exists())
        self.assertFalse(module.exists())
        self.assertFalse((self.state / 'registry' / (record['id'] + '.json')).exists())
        self.assertFalse((self.root / '휴지통').exists())
        self.assertTrue(other_source.exists()); self.assertTrue(other_module.exists())
        self.assertEqual(store.read(other['id'])['stage'], 'ready')

    def test_remove_failed_project_without_module(self):
        folder = self.state / 'projects/p_failed'; folder.mkdir(parents=True)
        (folder / 'download.txt').write_text('download')
        store.save({'id': 'p_failed', 'stage': 'failed'})
        self.assertTrue(lifecycle.remove('p_failed')['deleted'])
        self.assertFalse(folder.exists())

    def test_rejects_deleting_a_builtin_module(self):
        record, source, module = self.project()
        (module / 'module.json').write_text(json.dumps({'id': record['module_id']}))
        with self.assertRaisesRegex(ValueError, '소유한'): lifecycle.remove(record['id'])
        self.assertTrue(module.exists()); self.assertTrue(source.exists())

    def test_partial_removal_keeps_a_retryable_record(self):
        record, source, module = self.project()
        real = lifecycle.shutil.rmtree
        def locked(path, **kwargs):
            if path == self.state / 'projects' / record['id']: raise PermissionError('file locked')
            return real(path, **kwargs)
        with patch.object(lifecycle.shutil, 'rmtree', locked), self.assertRaises(ValueError): lifecycle.remove(record['id'])
        self.assertEqual(store.read(record['id'])['stage'], 'removal_failed')
        self.assertTrue(lifecycle.remove(record['id'])['permanent'])

    def test_installer_automatically_registers_mcp_before_ready(self):
        source = self.root / 'fixture'; source.mkdir(); (source / 'package.json').write_text('{}')
        record = {'id': 'p_automatic', 'repository': 'sample/automatic', 'url': 'https://github.com/sample/automatic', 'title': 'Automatic', 'environment': {}}
        spec = {'kind': 'node-mcp', 'directory': '.'}
        with patch.object(adapters, 'detect', return_value=spec), patch.object(adapters, 'prepare'), \
             patch.object(runtime, 'verify'), patch.object(runtime, 'verify_ui', return_value=False), \
             patch.object(installer, 'run_command'), patch.object(agent_tasks, 'link_when_idle', return_value={'connected': True, 'tools': 3}) as link:
            import threading
            installer.install(record, threading.Event(), source)
        link.assert_called_once()
        saved = store.read('p_automatic')
        self.assertEqual(saved['stage'], 'awaiting_activation')
        self.assertTrue(saved['agent_connection']['connected'])
        metadata = json.loads((self.root / 'modules' / saved['module_id'] / 'module.json').read_text(encoding='utf8'))
        self.assertEqual(metadata['group'], {'id': 'projects', 'title': 'GitHub'})
        self.assertEqual(metadata['app_title'], 'Automatic')
        generated = self.root / 'modules' / saved['module_id'] / 'frontend/register.ts'
        self.assertIn('ProjectApp', generated.read_text())


if __name__ == '__main__': unittest.main()
