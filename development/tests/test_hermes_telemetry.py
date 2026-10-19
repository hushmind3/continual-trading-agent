"""Actual owned decoder timings remain available for short responses."""
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from ai_agent.Hermes.chat import telemetry


class TelemetryTests(unittest.TestCase):
    def test_decoder_receipt_is_scoped_to_the_current_job(self):
        root=Path(__file__).resolve().parents[2]/'runtime/ai_agent/Hermes/verification'
        root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root,prefix='timing-') as folder:
            path=Path(folder)/'model.log'
            path.write_text('slot print_timing: id 0 | task 1 | eval time = 10 ms / 4 tokens (2 ms per token, 999 tokens per second)\n')
            worker=SimpleNamespace(model_log=SimpleNamespace(name=str(path)))
            telemetry.begin(worker)
            self.assertIsNone(telemetry.local_timing(worker))
            with path.open('a') as stream: stream.write('slot print_timing: id 0 | task 3 | eval time = 257.06 ms / 17 tokens (16.07 ms per token, 62.24 tokens per second)\n')
            self.assertEqual(telemetry.local_timing(worker),62.2)
            telemetry.begin(worker)
            self.assertIsNone(telemetry.local_timing(worker))

    def test_partial_and_non_decoder_lines_are_not_a_speed_sample(self):
        root=Path(__file__).resolve().parents[2]/'runtime/ai_agent/Hermes/verification'
        root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root,prefix='timing-') as folder:
            path=Path(folder)/'model.log';path.touch()
            worker=SimpleNamespace(model_log=SimpleNamespace(name=str(path)))
            telemetry.begin(worker)
            with path.open('a') as stream:stream.write('slot | prompt eval time = 20 ms / 3 tokens (1 ms per token, 999 tokens per second)\nslot | n_gen = 192, tg = 63.53 t/s')
            self.assertIsNone(telemetry.local_timing(worker))
            with path.open('a') as stream:stream.write(', tg_3s = 63.86 t/s\n')
            self.assertEqual(telemetry.local_timing(worker),63.5)


if __name__=='__main__':unittest.main()
