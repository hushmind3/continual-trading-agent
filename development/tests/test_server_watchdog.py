import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import server_watchdog as watchdog


class ServerWatchdogTests(unittest.TestCase):
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
