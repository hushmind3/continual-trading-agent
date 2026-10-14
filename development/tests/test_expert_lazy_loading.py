import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from stockrl.platform import assets


class ExpertLazyLoadingTests(unittest.TestCase):
    def test_unused_missing_package_does_not_block_selected_expert(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            settings=SimpleNamespace(model_dir=root,registry_file=root/'expert_registry.json',state_dir=root/'state')
            catalog={'active':['selected'],'experts':{
                'selected':{'name':'Selected','backend':'chronos_bolt','package':{'file':'valid.pt'}},
                'missing':{'package':{'file':'missing.pt'}}}}
            def package(path,reference):
                if reference['file']=='missing.pt':raise ValueError('missing package')
                return {'entry':{'backend':'chronos_bolt'},'module_count':1}
            with patch.object(assets,'read_catalog',return_value=catalog),patch.object(assets,'load_package',side_effect=package) as load:
                pool=assets.ExpertPool(settings)
                try:
                    load.assert_not_called()
                    self.assertEqual(pool.entry('selected')['backend'],'chronos_bolt')
                    pool.entry('selected');self.assertEqual(load.call_count,1)
                    with self.assertRaisesRegex(ValueError,'missing'):pool.entry('missing')
                    self.assertEqual(pool.entry('selected')['backend'],'chronos_bolt')
                finally:pool.close()


class ExpertRegistryIntegrityTests(unittest.TestCase):
    def test_partial_save_cannot_clear_another_models_registration(self):
        from stockrl.expert_registry import read_catalog,write_catalog
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);index=root/'expert_registry.json'
            entries={key:{'id':key,'name':key,'package':{'file':f'{key}/model.safetensors'}} for key in ('first','second')}
            write_catalog({'active':['first'],'experts':entries},index)
            before={path:path.read_bytes() for path in (index,root/'first/expert.json',root/'second/expert.json')}
            with self.assertRaisesRegex(ValueError,'without a delete request'):
                write_catalog({'active':[],'experts':{'test_only':{'package':{'file':'source.bin'}}}},index)
            self.assertEqual({path:path.read_bytes() for path in before},before)
            self.assertEqual(set(read_catalog(index)['experts']),{'first','second'})
            write_catalog({'active':['first'],'experts':{'first':entries['first']}},index,removed_ids=['second'])
            self.assertEqual(set(read_catalog(index)['experts']),{'first'})

    def test_invalid_or_missing_manifest_cannot_be_overwritten(self):
        from stockrl.expert_registry import write_catalog
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);index=root/'expert_registry.json'
            write_catalog({'experts':{'saved':{'package':{'file':'saved/model.safetensors'}}}},index)
            manifest=root/'saved/expert.json';before=index.read_bytes()
            for content in ('{broken',None):
                if content is None:manifest.unlink()
                else:manifest.write_text(content,encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'cannot be read'):
                    write_catalog({'experts':{}},index,removed_ids=['saved'])
                self.assertEqual(index.read_bytes(),before)
                if content is not None:self.assertEqual(manifest.read_text(encoding='utf-8'),content)
