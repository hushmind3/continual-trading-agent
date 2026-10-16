"""Adapter policy checks without loading a model or starting a live review."""
import ast
import importlib.util
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / 'modules/hermes/backend/engine'
spec = importlib.util.spec_from_file_location('hermes_execution', ENGINE / 'execution.py')
execution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(execution)


class ExecutionPolicyTests(unittest.TestCase):
    def test_chat_switch_overrides_legacy_policy(self):
        self.assertFalse(execution.request_policy({'read_only': True}, {'read_only': False})['read_only'])
        self.assertTrue(execution.request_policy({}, {'read_only': True})['read_only'])
        with self.assertRaises(ValueError):
            execution.request_policy({}, {'read_only': 'false'})

    def test_native_window_and_binding_preserve_other_settings(self):
        native = {'model': {'default': 'example', 'context_length': 98304}, 'agent': {'reasoning_effort': 'high'}}
        self.assertEqual(execution.context_window(native, 'example'), 98304)
        self.assertEqual(execution.context_window(native, 'another'), 0)
        self.assertEqual(execution.context_window({}, 'another'), 0)
        self.assertEqual(execution.context_window({'model': {'context_length': '81920'}}, 'another'), 81920)
        self.assertEqual(execution.context_window({'model': 'legacy'}, 'another'), 0)
        bound = execution.bind_model(native, 'another', 'http://127.0.0.1:12345/v1', 0)
        self.assertNotIn('context_length', bound['model'])
        self.assertEqual(bound['agent'], native['agent'])
        self.assertEqual(native['model']['default'], 'example')
        with self.assertRaises(ValueError):
            execution.context_window({'model': {'context_length': -1}}, 'example')

    def test_adapter_does_not_override_native_reasoning_or_output(self):
        tree = ast.parse((ENGINE / 'worker.py').read_text(encoding='utf-8'))
        call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'AIAgent')
        keys = {k.arg for k in call.keywords}
        self.assertTrue({'reasoning_config', 'max_tokens', 'skip_context_files'}.isdisjoint(keys))
        review = next(k.value for k in call.keywords if k.arg == 'skip_background_review')
        self.assertIsInstance(review, ast.Call)  # Read-only permission, not unconditional True.

    def test_review_keeps_worker_busy_until_native_completion(self):
        done = threading.Event()
        agent = SimpleNamespace(_background_review_run=SimpleNamespace(request_done=done))
        announced = threading.Event()
        worker = SimpleNamespace(agent=agent, stopping=False, lock=threading.RLock(), job={}, event=lambda *args: announced.set())
        thread = threading.Thread(target=execution.settle_review, args=(worker,))
        thread.start()
        try:
            self.assertTrue(announced.wait(timeout=1))
            self.assertTrue(thread.is_alive())
            self.assertEqual(worker.job['phase'], 'reviewing')
        finally:
            agent._background_review_run = None
            done.set()
            thread.join(timeout=1)
        self.assertFalse(thread.is_alive())


if __name__ == '__main__':
    unittest.main()
