"""Original provider hooks, real ASGI IPC, and agent ownership without model inference."""
import base64
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import harness, runtime, store


class HarnessTests(unittest.TestCase):
    def test_structured_response_preserves_json_without_tool_narration(self):
        text='```json\n{"reply":"actual tool result","tasks":[]}\n```\nTool finished.'
        value=json.loads(harness.format_response(text,'다음 JSON 객체만 반환하세요'))
        self.assertEqual(value,{'reply':'actual tool result','tasks':[]})
        with self.assertRaises(ValueError):harness.format_response('not JSON','JSON 객체만')
        self.assertEqual(harness.format_response('normal text','plain response'),'normal text')
    def setUp(self):
        base=ROOT/'runtime/projects/manage/verification';base.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=base);self.root=Path(self.temp.name)
        self.source=self.root/'projects/demo/source';self.source.mkdir(parents=True)
        (self.source/'ai_provider.py').write_text('async def compose(system,user,max_tokens=100): return "ORIGINAL"\nasync def status(): return {"mode":"original"}\n')
        (self.source/'main.py').write_text('from fastapi import FastAPI\nimport asyncio,ai_provider\napp=FastAPI()\nresult=None\n'
            '@app.get("/compose")\nasync def compose(): return {"text":await ai_provider.compose("SYSTEM","USER"),"model":await ai_provider.status()}\n'
            'async def work():\n global result\n result=await ai_provider.compose("BACKGROUND","TASK")\n'
            '@app.post("/submit")\nasync def submit():\n asyncio.create_task(work())\n return {"accepted":True}\n'
            '@app.get("/poll")\nasync def poll(): return {"result":result}\n')
        self.patch=patch.object(store,'STATE',self.root);self.patch.start()
        self.record={'id':'p_demo','active_source':str(self.source),'adapter':{'kind':'fastapi','directory':'.','app':'main:app'}}
        harness.configure(self.record,True);store.save(self.record)

    def tearDown(self):
        runtime.close();self.patch.stop();self.temp.cleanup()

    def test_hook_uses_original_ui_backend_without_editing_its_source(self):
        original=(self.source/'ai_provider.py').read_bytes()
        def execute(key,payload,cancelled):
            self.assertEqual(key,'p_demo')
            return {'mode':'hermes','name':'test'} if payload.get('operation')=='settings' else 'HERMES TOOL RESULT'
        with patch.object(harness,'execute',side_effect=execute):
            result=runtime.invoke(self.record,{'path':'/compose'})
        self.assertEqual(result['status'],200)
        self.assertEqual(json.loads(base64.b64decode(result['body'])),{'text':'HERMES TOOL RESULT','model':{'mode':'hermes','name':'test'}})
        self.assertEqual((self.source/'ai_provider.py').read_bytes(),original)

    def test_background_provider_request_does_not_block_polling(self):
        def execute(*args):time.sleep(.15);return 'BACKGROUND COMPLETE'
        with patch.object(harness,'execute',side_effect=execute):
            accepted=runtime.invoke(self.record,{'path':'/submit','method':'POST'})
            self.assertEqual(accepted['status'],200)
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                result=runtime.invoke(self.record,{'path':'/poll'})
                data=json.loads(base64.b64decode(result['body']))
                if data['result']:break
                time.sleep(.05)
            self.assertEqual(data['result'],'BACKGROUND COMPLETE')

    def test_coordinator_uses_real_agent_contract_and_rejects_incomplete(self):
        from ai_agent.Hermes.engine.bridge import bridge
        job={'state':'complete','session_id':'owned','text':'{"reply":"verified","tasks":[]}','events':[]}
        fake=Mock();fake.busy_reason.return_value=''
        fake.call.side_effect=lambda operation,payload=None: {'session':{'id':'owned'}} if operation=='session/create' else {'job':job}
        with patch('ai_agent.Hermes.engine.bridge.bridge',fake):
            result=harness.execute('p_demo',{'system':'JSON only','user':'owner request'},threading.Event())
        self.assertIn('verified',result)
        self.assertEqual(fake.call.call_args_list[1].args[1]['workspace'],str(self.source))
        self.assertEqual(store.read('p_demo')['harness']['session_id'],'owned')
        self.assertFalse(harness.ACTIVE)
        job['state']='paused'
        with patch('ai_agent.Hermes.engine.bridge.bridge',fake),self.assertRaisesRegex(ValueError,'완료'):
            harness.execute('p_demo',{'system':'JSON only','user':'owner request'},threading.Event())
        titles=[c.args[1]['title'] for c in fake.call.call_args_list if c.args[0]=='session/create']
        self.assertEqual(len(set(titles)),2)

    def test_switch_off_uses_original_provider(self):
        harness.configure(self.record,False);store.save(self.record)
        data=runtime.invoke(self.record,{'path':'/compose'})
        self.assertEqual(json.loads(base64.b64decode(data['body']))['text'],'ORIGINAL')

    def test_another_users_active_agent_is_not_started_or_stopped(self):
        fake=Mock();fake.busy_reason.return_value='user task'
        with patch('ai_agent.Hermes.engine.bridge.bridge',fake),self.assertRaisesRegex(ValueError,'다른 작업'):
            harness.execute('p_demo',{'system':'system','user':'request'},threading.Event())
        fake.call.assert_not_called()
        self.assertFalse(harness.ACTIVE)

    def test_control_cannot_answer_another_sessions_approval(self):
        self.record['harness'].update(session_id='owned',state='complete');store.save(self.record)
        fake=Mock();fake.call.return_value={'job':{'session_id':'other','state':'running','approval':{'kind':'tool','detail':'private'}}}
        with patch('ai_agent.Hermes.engine.bridge.bridge',fake),self.assertRaisesRegex(ValueError,'실행 중'):
            harness.control('p_demo',{'action':'answer','allow':True})
        self.assertEqual([c.args[0] for c in fake.call.call_args_list],['status'])


if __name__=='__main__':unittest.main()
