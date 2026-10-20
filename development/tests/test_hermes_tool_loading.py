"""Native direct surfaces must survive the platform's lazy-tool setting."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
sys.path.insert(0, str(ROOT / 'modules/hermes/backend/engine/upstream'))
from ai_agent.Hermes.engine.runtime_policy import configure_tools
from hermes_cli.config_defaults import DEFAULT_CONFIG


class ToolLoadingTests(unittest.TestCase):
    def configure(self, mode):
        config = {'tools': {'other': True}}
        worker = SimpleNamespace(native_config=lambda: config, write_config=lambda value: None)
        with patch('tools.registry.registry.get_tool_to_toolset_map', return_value={
            'web_search': 'web', 'computer_use': 'computer_use', 'read_file': 'file'}), \
             patch('tools.tool_search._DIRECT_SURFACE_TOOLSETS', {'web', 'computer_use'}):
            configure_tools(worker, mode)
        self.assertTrue(config['tools']['other'])
        return config['tools']['tool_search']

    def test_lazy_keeps_direct_tools_and_defers_others(self):
        self.assertEqual(self.configure('lazy'), {'enabled': 'auto', 'defer': ['read_file']})

    def test_native_preserves_original_defer_list(self):
        self.assertEqual(self.configure('native')['defer'], DEFAULT_CONFIG['tools']['tool_search']['defer'])

    def test_eager_has_no_deferred_tools(self):
        self.assertEqual(self.configure('eager'), {'enabled': 'off', 'defer': []})


if __name__ == '__main__':
    unittest.main()
