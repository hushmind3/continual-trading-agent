import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from platform_modules import discover,mount_namespaces,signature


class ModuleTests(unittest.TestCase):
    def fixture(self,root):
        folder=root/'example';(folder/'backend').mkdir(parents=True)
        namespace='module_test_'+uuid.uuid4().hex
        meta={'schema':1,'id':'example','group':{'id':'example','title':'예제'},'backend':{'namespace':namespace,'entry':'register'},'frontend':{'entry':'frontend/register.ts'}}
        (folder/'module.json').write_text(json.dumps(meta),encoding='utf8')
        (folder/'backend/register.py').write_text('VALUE=42\n',encoding='utf8')
        return folder,meta

    def test_namespace_entry_comes_from_added_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder,meta=self.fixture(root)
            records=discover(root);mount_namespaces(records)
            module=importlib.import_module(meta['backend']['namespace']+'.register')
            self.assertEqual(module.VALUE,42)
            self.assertTrue(Path(module.__file__).is_relative_to(folder))

    def test_folder_detach_and_return_change_only_discovery(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);root=base/'modules';root.mkdir();folder,_=self.fixture(root)
            before=signature(root);self.assertEqual(len(discover(root)),1)
            parked=base/'parked';folder.rename(parked)
            self.assertEqual(discover(root),[]);self.assertNotEqual(signature(root),before)
            parked.rename(folder)
            self.assertEqual(signature(root),before)

    def test_state_is_neither_created_nor_removed_by_discovery(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder,meta=self.fixture(root)
            meta['data']=['runtime/example'];(folder/'module.json').write_text(json.dumps(meta),encoding='utf8')
            discover(root)
            self.assertFalse((root/'runtime').exists())

    def test_module_cannot_point_to_an_unowned_backend(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder,meta=self.fixture(root)
            meta['backend']['path']='../../';(folder/'module.json').write_text(json.dumps(meta),encoding='utf8')
            with self.assertRaises(ValueError):discover(root)

    def test_installed_apps_share_github_without_rewriting_manifests_or_data(self):
        verification=Path(__file__).resolve().parents[2]/'runtime/projects/manage/verification'
        verification.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=verification) as temp:
            root=Path(temp);folder,meta=self.fixture(root)
            self.assertEqual(discover(root)[0]['group'],meta['group'])
            meta.update(install_revision='v1',data=['runtime/projects/manage/projects/p_example'])
            manifest=folder/'module.json';manifest.write_text(json.dumps(meta),encoding='utf8')
            before=manifest.read_bytes()
            record=discover(root)[0]
            self.assertEqual(record['group'],{'id':'projects','title':'GitHub'})
            self.assertEqual(record['data'],meta['data'])
            self.assertEqual(manifest.read_bytes(),before)
            self.assertFalse((root/'runtime').exists())

    def test_added_module_cannot_shadow_existing_namespace(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder,meta=self.fixture(root)
            other=root/'other';(other/'backend').mkdir(parents=True)
            (other/'module.json').write_text(json.dumps({**meta,'id':'other'}),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'namespace collision'):discover(root)


if __name__=='__main__':unittest.main()
