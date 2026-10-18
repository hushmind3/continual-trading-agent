"""Automatic local detachment, rollback, reconnection and residue ownership."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import detachment,lifecycle,installer,runtime,store,cleanup,requirements


class DetachmentTests(unittest.TestCase):
    def setUp(self):
        base=ROOT/'runtime/projects/manage/verification';base.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=base);self.root=Path(self.temp.name);self.state=self.root/'runtime/projects/manage'
        self.entries=[]
        self.patches=[patch.object(store,'ROOT',self.root),patch.object(store,'STATE',self.state),
            patch.object(installer,'ROOT',self.root),patch.object(installer,'STATE',self.state),
            patch.object(installer,'JOBS',{}),patch.object(installer,'RESTARTING',False),
            patch.object(runtime,'busy_reason',return_value=''),
            patch.dict(sys.modules,{'menu_registry':SimpleNamespace(MODULE_ENTRIES=self.entries)})]
        for item in self.patches:item.start()
    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        self.temp.cleanup()
    def wait(self,key):
        deadline=time.monotonic()+8
        while key in installer.JOBS and time.monotonic()<deadline:time.sleep(.02)
        self.assertNotIn(key,installer.JOBS)
        return store.read(key)
    def external(self):
        source=self.state/'projects/p_example/versions/v1/source';source.mkdir(parents=True)
        (source/'index.html').write_text('<h1>real program</h1>')
        (source/'private-data.txt').write_text('retain me')
        module=self.root/'modules/external_example';module.mkdir(parents=True)
        (module/'module.json').write_text('{"id":"external_example","install_revision":"v1"}')
        record={'id':'p_example','module_id':'external_example','stage':'ready','title':'Example','url':'https://github.com/example/app',
            'repository':'example/app','active_source':str(source),'adapter':{'kind':'static','directory':'.','output':'.'},'environment':{'APP_TOKEN':'private'}}
        store.save(record);return record,source,module
    def builtin(self):
        folder=self.root/'modules/rea';folder.mkdir(parents=True)
        (folder/'module.json').write_text('{"id":"rea"}')
        (folder/'program.py').write_text('original code')
        (folder/'.venv').mkdir();(folder/'.venv/installed.txt').write_text('private environment')
        data=self.root/'runtime/rea';data.mkdir(parents=True);(data/'result.txt').write_text('user result')
        entry=SimpleNamespace(busy_reason=Mock(return_value=''),reserve_restart=Mock(),close=Mock(),cancel_restart=Mock())
        self.entries.append(({'id':'rea','group':{'id':'rea','title':'REA'},'folder':folder,'data':['runtime/rea']},entry))
        def prepare(record,target,progress):target.mkdir(parents=True);(target/'modules').mkdir();return target
        return folder,data,entry,prepare
    def test_external_detach_is_runnable_without_download_or_manual_setup(self):
        record,source,module=self.external()
        result=detachment.start(record['id']);self.assertEqual(result['stage'],'detaching')
        saved=self.wait(record['id']);self.assertEqual(saved['stage'],'removed',saved.get('error'))
        target=Path(saved['standalone_path'])
        self.assertFalse(source.exists());self.assertFalse(module.exists())
        self.assertEqual((target/'source/private-data.txt').read_text(),'retain me')
        self.assertEqual(json.loads((target/'.runtime/environment.json').read_text())['APP_TOKEN'],'private')
        result=subprocess.run([sys.executable,'-I','-X','utf8',str(target/'run.py'),'check'],cwd=target,capture_output=True,text=True,encoding='utf8')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((target/'실행.cmd').is_file())
        lifecycle.reconnect(record['id'])
        self.assertTrue(module.exists());self.assertEqual(store.read(record['id'])['stage'],'awaiting_activation')
        self.assertFalse(list((self.state/'projects'/record['id']/'exports').glob('*.zip')))
    def test_builtin_moves_its_actual_environment_and_data_then_restores_them(self):
        folder,data,entry,prepare=self.builtin()
        with patch.object(detachment,'prepare',side_effect=prepare):
            detachment.start('rea');record=self.wait('rea')
        self.assertEqual(record['stage'],'removed',record.get('error'))
        target=Path(record['standalone_path']);self.assertFalse(folder.exists());self.assertFalse(data.exists())
        self.assertEqual((target/'modules/rea/.venv/installed.txt').read_text(),'private environment')
        (target/'modules/rea/program.py').write_text('updated code')
        (target/'runtime/rea/result.txt').write_text('updated result')
        (target/'extra-user-file.txt').write_text('preserve independent edits')
        lifecycle.reconnect('rea')
        self.assertEqual((folder/'program.py').read_text(),'updated code')
        self.assertEqual((data/'result.txt').read_text(),'updated result')
        self.assertFalse(target.exists())
        self.assertTrue(list((self.root/'휴지통').rglob('extra-user-file.txt')))
    def test_preparation_failure_preserves_original_program_and_releases_guard(self):
        folder,data,entry,prepare=self.builtin()
        with patch.object(detachment,'prepare',side_effect=RuntimeError('build failed')):
            detachment.start('rea');record=self.wait('rea')
        self.assertEqual(record['stage'],'ready');self.assertIn('build failed',record['error'])
        self.assertTrue(folder.exists());self.assertTrue(data.exists());entry.cancel_restart.assert_called_once()
    def test_cleanup_moves_only_generated_residue_to_trash(self):
        record,source,module=self.external()
        export=self.state/'projects/p_example/exports/old.zip';export.parent.mkdir();export.write_bytes(b'old export')
        result=cleanup.clean();self.assertEqual(result['files'],1)
        self.assertFalse(export.exists());self.assertTrue(source.exists());self.assertTrue(module.exists())
        self.assertEqual((self.root/'휴지통'/export.relative_to(self.root)).read_bytes(),b'old export')
    def test_documentation_repository_is_not_misrepresented_as_a_failed_app(self):
        source=self.root/'notes';(source/'docs').mkdir(parents=True);(source/'docs/analysis.md').write_text('research')
        with self.assertRaises(requirements.RequirementError) as result:requirements.check(source)
        self.assertEqual(result.exception.stage,'not_app')
    def test_abandoned_job_without_an_owner_pid_does_not_lock_installation_forever(self):
        store.save({'id':'p_abandoned','stage':'detaching'})
        with patch('psutil.Process') as process:
            result=installer.installed()
        process.assert_not_called()
        self.assertEqual(result[0]['stage'],'failed')


if __name__=='__main__':unittest.main()
