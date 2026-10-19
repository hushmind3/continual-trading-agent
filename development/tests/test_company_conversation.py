"""Unified chat forwards original records/actions without model execution."""
import base64
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import conversation


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.record = {'id': 'demo', 'stage': 'ready', 'workspace_ui': {'recipe': 'company-v1'}, 'harness': {'enabled': True}}
        self.calls = []
        self.lookup = patch.object(conversation.store, 'read', return_value=self.record)
        self.lookup.start(); self.addCleanup(self.lookup.stop)
        self.bridge = patch.object(conversation.runtime, 'invoke', side_effect=self.invoke)
        self.bridge.start(); self.addCleanup(self.bridge.stop)

    def invoke(self, record, payload, origin):
        self.calls.append(payload)
        path = payload['path']; status = 200
        if path == '/api/local/session': result = {'token': 'test-local-token'}
        elif path == '/api/admin/ceo': result = {'messages': [{'speaker': 'ceo', 'body': '**원본 기록**'}]}
        elif path == '/api/admin/control': result = {'ventures': [{'id': 'venture_demo', 'status': 'pending'}]}
        elif '/status/' in path: status, result = 404, {'detail': '서버 재시작으로 요청이 없습니다.'}
        elif path.endswith('/submit'): result = {'accepted': True, 'request_id': 'a' * 32}
        else: result = {'status': 'approved'}
        return {'status': status, 'body': base64.b64encode(json.dumps(result).encode()).decode()}

    def test_history_is_original_and_auth_is_not_returned(self):
        result = conversation.call('demo', {})
        self.assertEqual(result['messages'][0]['body'], '**원본 기록**')
        self.assertNotIn('test-local-token', json.dumps(result))
        self.assertTrue(all(c['method'] == 'GET' for c in self.calls))
        self.assertEqual(self.calls[1]['headers']['X-Project-Zero-Token'], 'test-local-token')

    def test_submit_uses_async_original_api_once(self):
        result = conversation.call('demo', {'action': 'send', 'message': '함께 기획하자'})
        self.assertTrue(result['accepted'])
        writes = [c for c in self.calls if c['method'] == 'POST']
        self.assertEqual(len(writes), 1)
        self.assertEqual(json.loads(base64.b64decode(writes[0]['body'])), {'message': '함께 기획하자'})
        self.assertTrue(writes[0]['path'].endswith('/chat/submit'))

    def test_approval_is_explicit_and_rejects_path_injection(self):
        conversation.call('demo', {'action': 'decision', 'venture_id': 'venture_demo', 'approve': False})
        self.assertEqual(json.loads(base64.b64decode(self.calls[-1]['body'])), {'approve': False})
        with self.assertRaises(ValueError): conversation.call('demo', {'action': 'decision', 'venture_id': '../other', 'approve': True})

    def test_removed_or_disconnected_apps_are_not_accessible(self):
        for change in ({'stage': 'removed'}, {'harness': {'enabled': False}}, {'workspace_ui': {}}):
            with patch.object(conversation.store, 'read', return_value={**self.record, **change}), self.assertRaises(ValueError):
                conversation.call('demo', {})
        self.assertEqual(self.calls, [])

    def test_restart_clears_pending_request_without_losing_history(self):
        result = conversation.call('demo', {'request_id': 'a' * 32})
        self.assertEqual(result['request']['status'], 'failed')
        self.assertEqual(len(result['messages']), 1)


if __name__ == '__main__': unittest.main()
