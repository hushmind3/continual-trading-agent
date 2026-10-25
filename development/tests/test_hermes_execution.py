"""Adapter policy checks without loading a model or starting a live review."""
import ast
import importlib.util
from pathlib import Path
import threading
import sys
import types
from unittest.mock import patch
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / 'modules/hermes/backend/engine'
spec = importlib.util.spec_from_file_location('hermes_execution', ENGINE / 'execution.py')
execution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(execution)
package=types.ModuleType('hermes_policy_test');package.__path__=[str(ENGINE)]
sys.modules['hermes_policy_test']=package
policy_spec=importlib.util.spec_from_file_location('hermes_policy_test.runtime_policy',ENGINE/'runtime_policy.py')
policy=importlib.util.module_from_spec(policy_spec);policy_spec.loader.exec_module(policy)


class ExecutionPolicyTests(unittest.TestCase):
    def test_model_profiles_do_not_leak_between_models(self):
        cfg={'model':'ornith','tool_loading':'lazy','model_options':{}}
        policy.save_options(cfg,{'context_length':65536,'thinking_mode':'off','max_output_tokens':0,'reasoning_effort':'auto'})
        self.assertEqual(policy.model_options(cfg,{}),{'context_length':65536,'thinking_mode':'off','max_output_tokens':0,'reasoning_effort':'auto'})
        self.assertEqual(policy.model_options({**cfg,'model':'another'},{}),{'context_length':0,'thinking_mode':'auto','max_output_tokens':0,'reasoning_effort':'auto'})
        for value in (True,-1,0.5,'65536',2097153):
            with self.subTest(value=value),self.assertRaises(ValueError):policy.save_options(cfg,{'context_length':value})
        policy.save_options(cfg,{'context_length':0,'thinking_mode':'auto'})
        self.assertEqual(policy.model_options(cfg,{})['context_length'],0)

    def test_thinking_override_preserves_other_native_request_fields(self):
        agent=SimpleNamespace(request_overrides={'extra_body':{'existing':1,'chat_template_kwargs':{'other':True}}})
        policy.apply_thinking(agent,{'thinking_mode':'off'},True)
        self.assertEqual(agent.request_overrides['extra_body'],{'existing':1,'chat_template_kwargs':{'other':True,'enable_thinking':False}})
        policy.apply_thinking(agent,{'thinking_mode':'on'},True)
        self.assertTrue(agent.request_overrides['extra_body']['chat_template_kwargs']['enable_thinking'])
        untouched=SimpleNamespace(request_overrides={})
        policy.apply_thinking(untouched,{'thinking_mode':'auto'},True)
        policy.apply_thinking(untouched,{'thinking_mode':'off'},False)
        self.assertEqual(untouched.request_overrides,{})

    def test_lazy_tool_delivery_keeps_registry_capabilities_and_native_default(self):
        native={'tools':{'tool_search':{'listing_max_tokens':4000,'defer':[]}}}
        defaults={'tools':{'tool_search':{'defer':['computer_use']}}}
        registry=SimpleNamespace(get_tool_to_toolset_map=lambda:{'terminal':'terminal','computer_use':'computer_use'})
        worker=SimpleNamespace(native_config=lambda:native,write_config=lambda value:None)
        with patch.dict(sys.modules,{'hermes_cli.config_defaults':SimpleNamespace(DEFAULT_CONFIG=defaults),'tools.registry':SimpleNamespace(registry=registry),'tools.tool_search':SimpleNamespace(_DIRECT_SURFACE_TOOLSETS=set())}):
            policy.configure_tools(worker,'lazy')
            self.assertEqual(native['tools']['tool_search']['defer'],['computer_use','terminal'])
            self.assertEqual(native['tools']['tool_search']['listing_max_tokens'],4000)
            policy.configure_tools(worker,'native')
            self.assertEqual(native['tools']['tool_search']['defer'],['computer_use'])
            policy.configure_tools(worker,'eager')
            self.assertEqual(native['tools']['tool_search']['enabled'],'off')

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
        self.assertNotIn('max_tokens',keys)
        self.assertIn('reasoning_config',keys)
        self.assertIn('skip_context_files',keys)
        reasoning = next(k.value for k in call.keywords if k.arg == 'reasoning_config')
        self.assertIsInstance(reasoning, ast.IfExp)  # Provider-specific override only.
        review = next(k.value for k in call.keywords if k.arg == 'skip_background_review')
        self.assertIsInstance(review, ast.BoolOp)  # Read-only permission, not unconditional True.

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
