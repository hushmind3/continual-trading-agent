"""Codex provider routing and credential boundaries without a model call."""
import sys
import unittest
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
sys.path.insert(0, str(ROOT / 'backend/ai_agent/choki/engine/upstream'))
from ai_agent.choki.models.codex import CodexConnection, runtime, goal_reasoning
from ai_agent.choki.engine.execution import bind_model
from ai_agent.choki.chat import telemetry
from types import SimpleNamespace


class CodexTests(unittest.TestCase):
    def setUp(self):
        # Provider tests must never inherit a developer's live model or credential pool.
        for target,value in [('hermes_cli.config.load_config', {'model': {'default':'contract-model','provider':'custom'}}),
                             ('hermes_cli.runtime_provider._resolve_from_pool', None)]:
            item=patch(target,return_value=value);item.start();self.addCleanup(item.stop)

    def test_cloud_goal_reasoning_restores_original_local_auxiliary_options(self):
        native={'auxiliary':{'goal_judge':{'extra_body':{'other':True,'reasoning':{'effort':'low'}}}}}
        worker=SimpleNamespace(codex=SimpleNamespace(reasoning=lambda *args:{'enabled':True,'effort':'high'}))
        goal_reasoning(worker,native,{'provider':'openai-codex','model':'selected'},{'reasoning_effort':'high'})
        self.assertEqual(native['auxiliary']['goal_judge']['extra_body']['reasoning']['effort'],'high')
        goal_reasoning(worker,native,{'provider':'custom'},{})
        self.assertEqual(native,{'auxiliary':{'goal_judge':{'extra_body':{'other':True,'reasoning':{'effort':'low'}}}}})

    def test_existing_login_does_not_start_duplicate_pending_grant(self):
        with patch('hermes_cli.auth.get_codex_auth_status',return_value={'logged_in':True}), \
             patch('hermes_cli.auth_codex._codex_request_device_code') as request:
            result=CodexConnection().start()
        self.assertEqual(result,{'state':'complete','connected':True})
        request.assert_not_called()

    def test_account_catalog_keeps_all_visible_models_and_capabilities(self):
        entries=[{'slug':name,'display_name':name.upper(),'visibility':'list','default_reasoning_level':'low',
                  'supported_reasoning_levels':[{'effort':'high','description':'deep'},{'effort':'low'},{'effort':'ultra'}]}
                 for name in ('gpt-6.1-sol','gpt-6-astra','gpt-6-sol')]
        entries.append({'slug':'internal-only','visibility':'hide'})
        connection=CodexConnection()
        with patch('hermes_cli.auth_codex.resolve_codex_runtime_credentials',return_value={'api_key':'private','base_url':'https://owned.example'}), \
             patch('agent.codex_headers.codex_account_headers',return_value={}), \
             patch('agent.model_metadata.fetch_codex_catalog_entries',return_value=(entries,200)):
            result=connection.models()
        self.assertEqual([row['id'] for row in result['models']],['gpt-6.1-sol','gpt-6-astra','gpt-6-sol'])
        self.assertEqual([row['value'] for row in result['models'][0]['reasoning_efforts']],['high','low','ultra'])
        self.assertEqual(connection.reasoning('gpt-6.1-sol','auto'),{'enabled':True,'effort':'low'})
        self.assertNotIn('private',str(result))
        with self.assertRaises(ValueError):connection.reasoning('gpt-6.1-sol','ultra')
        from agent.transports.codex import _resolve_reasoning
        effort,enabled=_resolve_reasoning('gpt-6.1-sol',{'provider':'openai-codex','base_url':'https://chatgpt.com/backend-api/codex',
            'reasoning_config':connection.reasoning('gpt-6.1-sol','high')})
        self.assertEqual((effort,enabled),('high',True))

    def test_custom_route_is_unchanged_and_does_not_resolve_oauth(self):
        with patch('hermes_cli.auth_codex.resolve_codex_runtime_credentials') as resolve:
            self.assertEqual({k:v for k,v in runtime({'provider':'custom','base_url': 'http://localhost/v1','api_key':'local'}).items() if k in ('provider','api_mode','base_url','api_key')},
                {'provider': 'custom', 'api_mode': 'chat_completions', 'base_url': 'http://localhost/v1', 'api_key': 'local'})
            resolve.assert_not_called()

    def test_codex_uses_native_responses_and_credential_owned_host(self):
        with patch('hermes_cli.runtime_provider.resolve_codex_runtime_credentials',
                   return_value={'api_key': 'secret', 'base_url': 'https://owned.example/v1'}):
            result = runtime({'provider': 'openai-codex', 'base_url': 'https://untrusted.example', 'api_key': 'old-key'})
        self.assertEqual({k:v for k,v in result.items() if k in ('provider','api_mode','api_key','base_url')}, {'provider': 'openai-codex', 'api_mode': 'codex_responses',
                                 'api_key': 'secret', 'base_url': 'https://owned.example/v1'})

    def test_status_never_exposes_credentials(self):
        with patch('hermes_cli.auth.get_codex_auth_status', return_value={
            'logged_in': True, 'api_key': 'secret', 'access_token': 'secret', 'refresh_token': 'secret'}):
            self.assertEqual(CodexConnection().status(), {'state': 'idle', 'connected': True})

    def test_login_saves_independent_native_grant_without_activating_provider(self):
        connection = CodexConnection()
        with patch('hermes_cli.auth_codex._codex_poll_authorization_code', return_value={}), \
             patch('hermes_cli.auth_codex._codex_exchange_authorization_code', return_value={
                 'access_token': 'access', 'refresh_token': 'refresh', 'other': 'private'}), \
             patch('hermes_cli.auth_codex._save_codex_tokens') as save:
            connection._complete({'device_auth_id': 'device', 'user_code': 'code', 'interval': 5})
            save.assert_called_once_with({'access_token': 'access', 'refresh_token': 'refresh'}, set_active=False)
        self.assertEqual(connection.login, {'state': 'complete'})

    def test_provider_errors_do_not_leak_secret_bodies(self):
        connection = CodexConnection()
        with patch('hermes_cli.auth_codex._codex_poll_authorization_code', side_effect=RuntimeError('secret-token')):
            connection._complete({'device_auth_id': 'device', 'user_code': 'code', 'interval': 5})
        self.assertEqual(connection.login['state'], 'failed')
        self.assertNotIn('secret-token', str(connection.login))

    def test_bind_provider_does_not_copy_another_models_context(self):
        native = {'model': {'default': 'local', 'context_length': 65536}, 'other': {'keep': True}}
        result = bind_model(native, 'selected-cloud-model', 'https://owned.example', 0, 'openai-codex')
        self.assertEqual(result['model']['provider'], 'openai-codex')
        self.assertNotIn('context_length', result['model'])
        self.assertEqual(native['model']['context_length'], 65536)

    def test_cloud_metrics_do_not_read_retained_local_model_slots(self):
        worker = SimpleNamespace(job={'local_inference': False, 'started_at': time.time()},
            agent=SimpleNamespace(session_input_tokens=8, session_output_tokens=3, session_api_calls=1),
            model_process=SimpleNamespace(poll=lambda: None))
        with patch.object(telemetry, 'urlopen') as http, patch.object(telemetry, 'local_timing') as timing:
            metrics = telemetry.update(worker)
        http.assert_not_called(); timing.assert_not_called()
        self.assertEqual(metrics['output_tokens'], 3)
        self.assertNotIn('generation_tps', metrics)


if __name__ == '__main__':
    unittest.main()
