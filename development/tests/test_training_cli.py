import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
import pandas as pd
from stockrl.finrl.policy_learning import official_cli


class TrainingCLITests(unittest.TestCase):
    def test_checkpoint_goes_to_trainer_and_not_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);instances=[]
            def registry(*,champion=None):
                instance=Mock();instances.append(instance);return instance
            frame=pd.DataFrame([{'symbol':'A','date':'2026-01-01','close':100}])
            args=['official_cli','train','--currency','KRW','--resume','--champion-path','model.pt','--checkpoint','pinned.zip','--total-timesteps','1024']
            with patch.object(official_cli,'ROOT',root),patch.object(official_cli,'ExpertRegistry',side_effect=registry), \
                    patch.object(official_cli,'prices',return_value=frame),patch.object(official_cli,'train') as train, \
                    patch('stockrl.platform.sac_champion.load_spec',return_value={'identity':{}}), \
                    patch('stockrl.platform.system_operations.system.close_models'),patch('sys.argv',args):
                official_cli.main()
            self.assertEqual(train.call_args.kwargs['source_checkpoint'],Path('pinned.zip'))
            self.assertTrue(train.call_args.args[2])
            self.assertEqual(train.call_args.args[7],1024)
            self.assertEqual(len(instances),2)
            for instance in instances:instance.close.assert_called_once_with(cleanup=True)
