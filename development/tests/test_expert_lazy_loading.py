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
