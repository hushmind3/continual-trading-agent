"""Unified chat forwards original records/actions without model execution."""
import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import conversation, runtime, python_packages, company_context


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.record = {'id': 'demo', 'stage': 'ready', 'workspace_ui': {'recipe': 'company-v1'}, 'harness': {'enabled': True}}
        self.calls = []
        self.lookup = patch.object(conversation.store, 'read', return_value=self.record)
        self.lookup.start(); self.addCleanup(self.lookup.stop)
        self.bridge = patch.object(conversation.runtime, 'invoke', side_effect=self.invoke)
        self.bridge.start(); self.addCleanup(self.bridge.stop)

    def invoke(self, record, payload, origin=None):
        self.calls.append(payload)
        path = payload['path']; status = 200
        if path == '/api/local/session': result = {'token': 'test-local-token'}
        elif path == '/api/admin/ceo': result = {'messages': [{'speaker': 'ceo', 'body': '**원본 기록**'}]}
        elif path == '/api/admin/control': result = {'ventures': [{'id': 'venture_demo', 'status': 'pending'}]}
        elif path == '/api/store/info': result = {'published': False, 'payment_connected': False, 'usage': {'requests': 7}, 'product_url': None}
        elif path == '/api/admin/dashboard': result = {'counts': {'jobs_done': 2, 'jobs_pending': 0}, 'jobs': [{'role': 'CTO', 'status': 'failed', 'error': 'TimeoutError', 'mode': 'incomplete'}]}
        elif '/status/' in path: status, result = 404, {'detail': '서버 재시작으로 요청이 없습니다.'}
        elif path.endswith('/submit'): result = {'accepted': True, 'request_id': 'a' * 32}
        else: result = {'status': 'approved'}
        return {'status': status, 'body': base64.b64encode(json.dumps(result).encode()).decode()}

    def test_history_is_original_and_auth_is_not_returned(self):
        result = conversation.call('demo', {})
        self.assertEqual(result['messages'][0]['body'], '**원본 기록**')
        self.assertEqual(result['progress']['usage']['requests'], 7)
        self.assertNotIn('test-local-token', json.dumps(result))
        self.assertTrue(all(c['method'] == 'GET' for c in self.calls))
        self.assertEqual(self.calls[1]['headers']['X-Project-Zero-Token'], 'test-local-token')

    def test_submit_uses_async_original_api_once(self):
        result = conversation.call('demo', {'action': 'send', 'message': '함께 기획하자'})
        self.assertTrue(result['accepted'])
        writes = [c for c in self.calls if c['method'] == 'POST']
        self.assertEqual(len(writes), 1)
        self.assertEqual(json.loads(writes[0]['body']), {'message': '함께 기획하자'})
        self.assertTrue(writes[0]['path'].endswith('/chat/submit'))

    def test_approval_is_explicit_and_rejects_path_injection(self):
        conversation.call('demo', {'action': 'decision', 'venture_id': 'venture_demo', 'approve': False})
        self.assertEqual(json.loads(self.calls[-1]['body']), {'approve': False})
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

    def test_company_prompt_uses_actual_job_errors_and_one_shared_model(self):
        with patch.dict(runtime.WORKERS, {'demo': object()}):
            system=company_context.grounded_system(self.record,'original company rules')
        self.assertIn('"separate_execution_model_required": false',system)
        self.assertIn('TimeoutError',system)
        self.assertIn('"jobs_done": 2',system)
        self.assertNotIn('test-local-token',system)
        self.assertTrue(all(c['method']=='GET' for c in self.calls))

    def test_other_application_prompts_are_unchanged(self):
        self.assertEqual(company_context.grounded_system({'workspace_ui':{}},'original'),'original')
        self.assertEqual(self.calls,[])

    def test_obsolete_assistant_connection_claims_are_not_current_model_evidence(self):
        rows=[{'speaker':'owner','body':'모델 연결 안 됐다고 했는데 왜 대답하나?'},
              {'speaker':'ceo','body':'실행 모델은 연결 안 됐습니다. 연결해 주세요.'},
              {'speaker':'ceo','body':'견적서 제품 요구사항을 작성했습니다.'}]
        user=json.dumps({'recent_chat':rows,'owner_instruction':'현재 상태 확인'},ensure_ascii=False)
        data=json.loads(company_context.grounded_user(self.record,user))
        self.assertEqual(data['recent_chat'],[rows[0],rows[2]])
        self.assertEqual(data['historical_connection_claims_omitted'],1)
        self.assertEqual(json.loads(user)['recent_chat'],rows)

    def test_real_asgi_child_receives_json_for_chat_and_approval(self):
        verification = Path(__file__).resolve().parents[2] / 'runtime/projects/manage/verification'
        verification.mkdir(parents=True, exist_ok=True)
        self.bridge.stop()
        with tempfile.TemporaryDirectory(dir=verification, prefix='conversation-ipc-') as directory:
            source = Path(directory) / 'source'
            source.mkdir()
            self.record['harness']['entry']=''
            (source / 'server.py').write_text('''from fastapi import FastAPI,Header,HTTPException
app=FastAPI()
@app.get('/api/local/session')
def session(): return {'token':'fixture-token'}
@app.post('/api/admin/ceo/chat/submit')
def submit(body:dict,x_project_zero_token:str=Header('')):
    if x_project_zero_token!='fixture-token':raise HTTPException(401)
    return {'accepted':True,'request_id':'a'*32,'received':body}
@app.post('/api/admin/ventures/{venture_id}/decision')
def decision(venture_id:str,body:dict,x_project_zero_token:str=Header('')):
    if x_project_zero_token!='fixture-token':raise HTTPException(401)
    return {'id':venture_id,'received':body}
''', encoding='utf-8')
            self.record.update(active_source=str(source), adapter={'kind':'fastapi','app':'server:app'})
            with patch.dict(runtime.WORKERS, clear=True), patch.object(conversation.store,'project_folder',return_value=source), patch.object(python_packages,'folder',return_value=source/'packages'):
                try:
                    sent=conversation.call('demo',{'action':'send','message':'한글 실제 전송'})
                    self.assertEqual(sent['received'],{'message':'한글 실제 전송'})
                    decision=conversation.call('demo',{'action':'decision','venture_id':'venture_fixture','approve':False})
                    self.assertEqual(decision['received'],{'approve':False})
                finally:
                    for worker in runtime.WORKERS.values(): worker.close()


if __name__ == '__main__': unittest.main()
