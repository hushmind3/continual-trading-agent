import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import server_watchdog as watchdog


class ServerWatchdogTests(unittest.TestCase):
    def test_module_remove_is_detected_even_when_disk_returns_to_previous_signature(self):
        with patch.object(watchdog,'read_json',return_value={}),patch.object(watchdog,'api',return_value={'module_signature':'intermediate-app'}):
            self.assertTrue(watchdog.modules_changed('original','original'))

    def test_live_module_signature_prevents_unnecessary_restart(self):
        with patch.object(watchdog,'read_json',return_value={}),patch.object(watchdog,'api',return_value={'module_signature':'current'}):
            self.assertFalse(watchdog.modules_changed('current','stale-record'))

    def test_stale_frontend_build_is_reconciled_even_when_api_matches_disk(self):
        applied={'sources':{'frontend':{'modules/.registration':'old'}}}
        with patch.object(watchdog,'read_json',return_value=applied),patch.object(watchdog,'api',return_value={'module_signature':'current'}):
            self.assertTrue(watchdog.modules_changed('current','current'))

    def test_healthy_server_is_not_restarted(self):
        with patch.object(watchdog,'ready',return_value=True),patch.object(watchdog,'main') as launch:
            self.assertFalse(watchdog.recover())
            launch.assert_not_called()

    def test_unresponsive_listener_is_not_killed_or_replaced(self):
        with patch.object(watchdog,'ready',return_value=False),patch.object(watchdog,'listeners',return_value=[(1,2,'api')]),patch.object(watchdog,'main') as launch:
            self.assertFalse(watchdog.recover())
            launch.assert_not_called()

    def test_empty_port_recovers_api_without_starting_finance(self):
        with patch.object(watchdog,'ready',side_effect=[False,True]),patch.object(watchdog,'listeners',return_value=[]),patch.object(watchdog,'main') as launch:
            self.assertTrue(watchdog.recover())
            launch.assert_called_once_with(apply_only=True,skip_build=True,skip_checks=True,watchdog=False)

    def test_foreign_port_owner_is_not_replaced(self):
        with patch.object(watchdog,'ready',return_value=False),patch.object(watchdog,'listeners',side_effect=RuntimeError('foreign service')),patch.object(watchdog,'main') as launch:
            with self.assertRaisesRegex(RuntimeError,'foreign service'):watchdog.recover()
            launch.assert_not_called()


if __name__=='__main__':unittest.main()
