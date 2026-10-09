"""Shared market/reward/experience contracts and cold command imports."""
import json
import os
import pickle
import subprocess
import sys
import unittest
from dataclasses import fields
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SharedInfrastructureTests(unittest.TestCase):
    def child(self, source):
        environment = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONUTF8='1')
        result = subprocess.run([sys.executable, '-c', source], cwd=ROOT, env=environment,
            capture_output=True, text=True, encoding='utf-8', timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout.splitlines()[-1])





    def test_cli_feed_help_and_disabled_train_do_not_load_models(self):
        report = self.child("""
import json, sys
from stockrl import cli
sys.argv = ['stockrl', 'web', '--help']
try: cli.main()
except SystemExit as error: assert error.code == 0
sys.argv = ['stockrl', 'train']
try: cli.main()
except SystemExit as error: assert error.code == 2
print(json.dumps({'torch': 'torch' in sys.modules, 'legacy': 'stockrl.global_online' in sys.modules,
    'numpy': 'numpy' in sys.modules}))
""")
        self.assertEqual(report, {'torch': False, 'legacy': False, 'numpy': False})

    def test_actual_feed_imports_and_moe_module_are_independent_of_old_models(self):
        report = self.child("""
import importlib.abc, json, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {'stockrl.global_transformer', 'stockrl.global_online', 'stockrl.market_training'}:
            raise RuntimeError('unexpected legacy import: ' + fullname)
sys.meta_path.insert(0, Block())
import stockrl.cli, stockrl.live_feed
feed_loaded_torch = 'torch' in sys.modules
import stockrl.trading_moe
print(json.dumps({'feed_loaded_torch': feed_loaded_torch, 'moe':  hasattr(stockrl.trading_moe, 'EvidenceAdapter'),
    'legacy': 'stockrl.global_transformer' in sys.modules}))
""")
        self.assertEqual(report, {'feed_loaded_torch': False, 'moe': True, 'legacy': False})


if __name__ == '__main__': unittest.main()
