import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from stockrl.management.connection_settings import provider_credentials as credentials


class ProviderSettingsPathTests(unittest.TestCase):
    def test_read_and_save_use_project_config_after_module_move(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root/'configs/local/provider_settings.json'
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({'provider': 'kiwoom', 'environment': 'real'}))
            with patch.object(credentials, 'ROOT', root), patch.dict(credentials.os.environ, {}, clear=True), \
                    patch.object(credentials, 'ensure_project_path', side_effect=lambda path, label: path):
                self.assertEqual(credentials.read_settings(root/'runtime')['provider'], 'kiwoom')
                credentials._write_settings(root/'runtime', {'provider': 'kiwoom', 'environment': 'paper'})
                self.assertEqual(json.loads(settings.read_text())['environment'], 'paper')
                self.assertFalse((root/'backend/stockrl/configs').exists())

    def test_explicit_project_local_config_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            configured = Path(directory)/'local_settings'
            with patch.dict(credentials.os.environ, {'STOCKRL_LOCAL_CONFIG_DIR': str(configured)}), \
                    patch.object(credentials, 'ensure_project_path', side_effect=lambda path, label: path):
                self.assertEqual(credentials._settings_path(), configured/'provider_settings.json')
