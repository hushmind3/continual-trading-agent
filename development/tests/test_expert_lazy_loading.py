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


class JsonExpertImportTests(unittest.TestCase):
    def test_json_package_import_keeps_native_files_without_loading_or_creating_pt(self):
        import json
        from stockrl.platform import library_store
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'market/model/MODEL.json';source.parent.mkdir(parents=True)
            package={'format':library_store.PACKAGE_FORMAT,'id':'existing','executor':'llama_cpp','feature_size':6,'module_count':1,'state_dict':{},'weight_asset':{'file':'market/model/GGUF.gguf','bytes':100,'sha256':'stored'},'entry':{'name':'Existing GGUF','backend':'gguf_market'}}
            source.write_text(json.dumps(package),encoding='utf-8');before=source.read_bytes()
            with patch.object(library_store.torch,'load',side_effect=AssertionError('must not load weights')),patch.object(library_store,'atomic_torch_save',side_effect=AssertionError('must not create PT')):
                item=library_store.import_package(SimpleNamespace(model_dir=root),source,'existing','chosen',lambda **values:None)
            self.assertEqual(item['id'],'chosen');self.assertEqual(item['package']['file'],'market/model/MODEL.json')
            self.assertTrue(item['input']['supported']);self.assertEqual(source.read_bytes(),before)
            self.assertEqual(list(root.rglob('*.pt')),[])


class CatalogReadScopeTests(unittest.TestCase):
 def test_one_response_reuses_reads_but_next_response_observes_json_edits(self):
  import json
  from stockrl import expert_registry as registry
  with tempfile.TemporaryDirectory() as temporary:
   path=Path(temporary)/'registry.json'
   path.write_text(json.dumps({'experts':{'first':{}},'active':[]}))
   with patch.object(registry,'_load_catalog',wraps=registry._load_catalog) as load:
    with registry.catalog_read_scope():
     self.assertIn('first',registry.read_catalog(path)['experts'])
     self.assertIn('first',registry.read_catalog(path)['experts'])
    self.assertEqual(load.call_count,1)
    path.write_text(json.dumps({'experts':{'second':{}},'active':[]}))
    with registry.catalog_read_scope():
     self.assertEqual(list(registry.read_catalog(path)['experts']),['second'])
    self.assertEqual(load.call_count,2)
 def test_failed_response_cannot_leave_a_registry_snapshot_cached(self):
  import json
  from stockrl import expert_registry as registry
  with tempfile.TemporaryDirectory() as temporary:
   path=Path(temporary)/'registry.json';path.write_text(json.dumps({'experts':{},'active':[]}))
   with self.assertRaises(RuntimeError):
    with registry.catalog_read_scope():
     registry.read_catalog(path)
     raise RuntimeError('response failed')
   path.write_text('invalid json')
   with self.assertRaises(ValueError):registry.read_catalog(path)
