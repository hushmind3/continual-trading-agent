"""Long live work, stalled work, cancellation acknowledgement and ownership."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import execution_watch as watch


class WatchTests(unittest.TestCase):
    def bridge(self, samples):
        clock = {'now': 0}; calls = []
        def call(operation, payload=None):
            calls.append((operation, payload))
            if operation == 'stop': return {}
            now, state, tokens = samples.pop(0); clock['now'] = now
            return {'job': {'session_id': 'owned', 'state': state, 'metrics': {'context_tokens': tokens, 'elapsed_seconds': now}}}
        bridge = Mock(); bridge.call.side_effect = call
        return bridge, clock, calls

    def test_real_progress_allows_execution_longer_than_900_seconds(self):
        bridge, clock, calls = self.bridge([(0,'running',0),(500,'running',50),(1000,'running',100),(1500,'complete',150)])
        cancel=Mock();cancel.is_set.return_value=False
        with patch.object(watch.time,'monotonic',side_effect=lambda:clock['now']):
            self.assertEqual(watch.wait_owned(bridge,'owned',cancel,True)['state'],'complete')
        self.assertFalse(any(op=='stop' for op,_ in calls))

    def test_elapsed_clock_alone_is_not_progress_and_stop_is_acknowledged(self):
        bridge,clock,calls=self.bridge([(0,'running',0),(901,'running',0),(902,'stopping',0),(903,'stopped',0)])
        cancel=Mock();cancel.is_set.return_value=False
        with patch.object(watch.time,'monotonic',side_effect=lambda:clock['now']),patch.object(watch.time,'sleep'):
            with self.assertRaisesRegex(ValueError,'진행이 없어'):watch.wait_owned(bridge,'owned',cancel,True)
        self.assertIn(('stop',{'session_id':'owned'}),calls)
        self.assertEqual(clock['now'],903)

    def test_changed_owner_is_never_stopped(self):
        bridge=Mock();bridge.call.return_value={'job':{'session_id':'other','state':'running'}}
        with self.assertRaisesRegex(ValueError,'소유권'):watch.wait_owned(bridge,'owned',Mock(),True)
        self.assertEqual([c.args[0] for c in bridge.call.call_args_list],['status'])

    def test_cancel_waits_for_native_terminal_state(self):
        bridge,clock,calls=self.bridge([(0,'running',0),(1,'stopping',0),(2,'stopped',0)])
        cancel=Mock();cancel.is_set.return_value=True
        with patch.object(watch.time,'sleep'):
            with self.assertRaisesRegex(ValueError,'소유자'):watch.wait_owned(bridge,'owned',cancel,True)
        self.assertEqual(clock['now'],2)


if __name__=='__main__':unittest.main()
