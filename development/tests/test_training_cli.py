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
                    patch.object(official_cli,'prices',return_value=frame) as prices,patch.object(official_cli,'train') as train, \
                    patch('stockrl.platform.sac_champion.load_spec',return_value={'identity':{}}), \
                    patch('stockrl.finrl.framework.policy_files',return_value=root), \
                    patch('stockrl.state_io.read_json',return_value={'timeframe':'1m'}), \
                    patch('stockrl.platform.system_operations.system.close_models'),patch('sys.argv',args):
                official_cli.main()
            self.assertEqual(train.call_args.kwargs['source_checkpoint'],Path('pinned.zip'))
            self.assertTrue(train.call_args.args[2])
            self.assertEqual(train.call_args.args[7],1024)
            prices.assert_called_once_with('KRW',None,timeframe='1m')
            self.assertEqual(len(instances),2)
            for instance in instances:instance.close.assert_called_once_with(cleanup=True)

    def test_changed_timeframe_rejected_before_prices_or_training(self):
        args=['official_cli','train','--resume','--checkpoint','pinned.zip','--timeframe','1m']
        with patch.object(official_cli,'ExpertRegistry'),patch.object(official_cli,'prices') as prices, \
                patch.object(official_cli,'train') as train, \
                patch('stockrl.finrl.framework.policy_files',return_value=Path('policies')), \
                patch('stockrl.state_io.read_json',return_value={'training_input':{'timeframe':'1d'}}), \
                patch('stockrl.platform.system_operations.system.close_models'),patch('sys.argv',args):
            with self.assertRaisesRegex(ValueError,'가격 주기'):official_cli.main()
        prices.assert_not_called();train.assert_not_called()
