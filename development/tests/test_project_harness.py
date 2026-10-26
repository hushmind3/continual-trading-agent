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
from platform_plugins.projects.harness_prompt import message_for


class HarnessTests(unittest.TestCase):
    def test_focused_prompt_rebuild_never_calls_native_host_or_repository_builder(self):
        from types import SimpleNamespace
        from ai_agent.choki.engine.runtime_policy import bind_discussion_context
        native=Mock(return_value='Current working directory: C:/금융매매모델')
        agent=SimpleNamespace(_build_system_prompt=native,_cached_system_prompt='old host prompt',
                              _cached_system_prompt_static='old',ephemeral_system_prompt='host rules')
        cfg={'application_context_scope':'focused_discussion','application_system_prompt':'당신은 CPO입니다.',
             'system_prompt':'사용자 지정 지침'}
        bind_discussion_context(agent,cfg)
        self.assertIsNone(agent._cached_system_prompt)
        for _ in range(2):
            prompt=agent._build_system_prompt('ignored native caller context')
            self.assertIn('CPO',prompt);self.assertIn('사용자 지정 지침',prompt)
            self.assertNotIn('금융',prompt);self.assertNotIn('working directory',prompt)
            self.assertNotIn('ignored native',prompt)
        native.assert_not_called();self.assertIsNone(agent.ephemeral_system_prompt)
        self.assertEqual(agent._cached_system_prompt_static,prompt)
        regular=SimpleNamespace(_build_system_prompt=native)
        bind_discussion_context(regular,{'application_context_scope':'native'})
        self.assertIs(regular._build_system_prompt,native)

    def test_conversational_json_is_a_reply_not_an_execution_phase(self):
        from platform_plugins.projects.harness_prompt import stage_for
        result=stage_for('당신은 CEO입니다. JSON 객체만',json.dumps({'_platform_turn':'dialogue','owner_instruction':'설계는 누가 해?'}))
        self.assertEqual(result,{'kind':'conversation','role':'CEO','label':'답변 작성'})

    def test_call_stage_separates_meeting_summary_and_employee_execution(self):
        from platform_plugins.projects.harness_prompt import stage_for
        self.assertEqual(stage_for('앱 (CFO)',json.dumps({'topic':'가격','prior_colleagues':[]})),{'kind':'meeting','role':'CFO','label':'회의 발언 작성'})
        self.assertEqual(stage_for('AI CEO',json.dumps({'topic':'가격','minutes':[]}))['kind'],'summary')
        self.assertEqual(stage_for('직원 CTO',json.dumps({'task':'파일 읽기'}))['kind'],'task')
        self.assertEqual(stage_for('당신은 CPO입니다.','주문 분석')['role'],'CPO')
        self.assertEqual(stage_for('응답을 작성하세요.','일반 요청')['role'],'')

    def test_plain_meeting_disables_execution_without_forcing_json(self):
        from types import SimpleNamespace
        from ai_agent.choki.engine.runtime_policy import apply_response_contract
        agent=SimpleNamespace(api_mode='chat_completions',request_overrides={'temperature':.3})
        apply_response_contract(agent,'',plan_only=True)
        self.assertEqual(agent.request_overrides['tools'],[])
        self.assertNotIn('response_format',agent.request_overrides)
        self.assertEqual(agent.request_overrides['temperature'],.3)

    def test_current_greeting_does_not_resume_historical_tool_requests(self):
        user=json.dumps({'recent_chat':[{'body':'Read verification/probe.txt'}], 'owner_instruction':'안녕'},ensure_ascii=False)
        result=message_for(user)
        self.assertTrue(result.endswith('Current instruction for this request ONLY:\n안녕'))
        self.assertIn('historical',result)
        self.assertNotIn('verification/probe.txt',result)
        self.assertTrue(message_for(json.dumps({'task':'CFO audit','owner_instruction':'Run the entire company'})).endswith('CFO audit'))

    def test_structured_native_transport_preserves_thinking_and_tools(self):
        from types import SimpleNamespace
        from ai_agent.choki.engine.runtime_policy import apply_response_contract
        agent=SimpleNamespace(api_mode='chat_completions',request_overrides={'extra_body':{'chat_template_kwargs':{'enable_thinking':True}}},tools=['read_file'])
        apply_response_contract(agent,'json_object')
        self.assertEqual(agent.request_overrides['response_format'],{'type':'json_object'})
        self.assertTrue(agent.request_overrides['extra_body']['chat_template_kwargs']['enable_thinking'])
        self.assertEqual(agent.tools,['read_file'])
        apply_response_contract(agent,'json_object',plan_only=True)
        self.assertEqual(agent.request_overrides['tools'],[])
        self.assertEqual(agent.request_overrides['tool_choice'],'none')
        self.assertTrue(agent.request_overrides['extra_body']['chat_template_kwargs']['enable_thinking'])

    def test_application_generation_is_validated_and_run_scoped(self):
        from types import SimpleNamespace
        from ai_agent.choki.engine.runtime_policy import application_generation,apply_application_generation
        agent=SimpleNamespace(max_tokens=9000,request_overrides={'extra_body':{'thinking':True}})
        options=application_generation({'max_tokens':2500,'temperature':.3})
        apply_application_generation(agent,options)
        self.assertEqual(agent.max_tokens,2500)
        self.assertEqual(agent.request_overrides['temperature'],.3)
        self.assertEqual(agent.request_overrides['extra_body'],{'thinking':True})
        for value in [{'max_tokens':True},{'max_tokens':0},{'temperature':float('nan')},{'unsupported':1}]:
            with self.assertRaises(ValueError):application_generation(value)

    def test_internal_origin_cannot_be_forged_in_an_app_payload(self):
        from starlette.requests import Request
        (self.source/'origin.py').write_text('from fastapi import FastAPI,Request\napp=FastAPI()\n@app.get("/")\ndef origin(request:Request):return {"client":request.client.host,"host":request.headers.get("host","")}\n')
        self.record.update(adapter={'kind':'fastapi','directory':'.','app':'origin:app'},harness={'enabled':False})
        origin=Request({'type':'http','method':'POST','scheme':'http','path':'/api','query_string':b'',
            'headers':[(b'host',b'127.0.0.1:8766')],'client':('203.0.113.9',5000),'server':('127.0.0.1',8766)})
        response=runtime.invoke(self.record,{'path':'/','_client':['127.0.0.1',1],'_host':'localhost'},origin)
        value=json.loads(base64.b64decode(response['body']))
        self.assertEqual(value['client'],'203.0.113.9')
        self.assertEqual(value['host'],'127.0.0.1:8766')
    def test_structured_response_preserves_json_without_tool_narration(self):
        text='```json\n{"reply":"actual tool result","tasks":[]}\n```\nTool finished.'
        value=json.loads(harness.format_response(text,'다음 JSON 객체만 반환하세요'))
        self.assertEqual(value,{'reply':'actual tool result','tasks':[]})
        with self.assertRaises(ValueError):harness.format_response('not JSON','JSON 객체만')
        retried='{"reply":"unfinished\n{"reply":"completed","tasks":[]}'
        self.assertEqual(json.loads(harness.format_response(retried,'JSON 객체만 {"reply":"text","tasks":[]}'))['reply'],'completed')
        with self.assertRaises(ValueError):harness.format_response('{"reply":"unfinished\n{"role":"CTO"}','JSON 객체만 {"reply":"text"}')
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
            if payload.get('operation')!='settings':self.assertEqual(payload['max_tokens'],100)
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
        from ai_agent.choki.engine.bridge import bridge
        job={'state':'complete','session_id':'owned','text':'{"reply":"verified","tasks":[]}','events':[]}
        fake=Mock();fake.busy_reason.return_value=''
        fake.call.side_effect=lambda operation,payload=None: {'session':{'id':'owned'}} if operation=='session/create' else {'job':job}
        with patch('ai_agent.choki.engine.bridge.bridge',fake):
            result=harness.execute('p_demo',{'system':'JSON only','user':'owner request','max_tokens':1700},threading.Event())
        self.assertIn('verified',result)
        self.assertEqual(fake.call.call_args_list[0].args[1]['workspace'],str(self.source))
        self.assertEqual(fake.call.call_args_list[0].args[1]['application_generation'],{})
        self.assertTrue(fake.call.call_args_list[0].args[1]['application_plan_only'])
        self.assertTrue(fake.call.call_args_list[0].args[1]['application_request'])
        self.assertEqual(store.read('p_demo')['harness']['session_id'],'owned')
        self.assertFalse(harness.ACTIVE)
        job['state']='paused'
        with patch('ai_agent.choki.engine.bridge.bridge',fake),self.assertRaisesRegex(ValueError,'완료'):
            harness.execute('p_demo',{'system':'JSON only','user':'owner request'},threading.Event())
        titles=[c.args[1]['title'] for c in fake.call.call_args_list if c.args[0]=='session/create']
        self.assertEqual(titles,[])

    def test_disabled_harness_status_does_not_contact_hermes_for_a_stale_session(self):
        self.record['harness'].update(session_id='previous',enabled=False,state='idle');store.save(self.record)
        with patch('ai_agent.choki.engine.bridge.bridge') as bridge:
            state=harness.status('p_demo')
            self.assertFalse(state['enabled']);bridge.call.assert_not_called()

    def test_measured_app_job_survives_a_different_hermes_job(self):
        metrics={'generation_tps':42.5,'input_tokens':300,'output_tokens':84,'api_calls':1}
        self.record['harness'].update(state='complete',session_id='owned');store.save(self.record)
        fake=Mock();fake.call.return_value={'job':{'session_id':'owned','state':'complete','metrics':metrics,'events':[]}}
        with patch('ai_agent.choki.engine.bridge.bridge',fake):
            self.assertEqual(harness.status('p_demo')['job']['metrics'],metrics)
            fake.call.return_value={'job':{'session_id':'someone-else','state':'running','metrics':{'generation_tps':999},'events':[]}}
            restored=harness.status('p_demo')['job']
            self.assertEqual(restored['session_id'],'owned')
            self.assertEqual(restored['metrics'],metrics)

    def test_unmeasured_new_request_does_not_show_previous_job_metrics(self):
        self.record['harness'].update(state='waiting',session_id=None,last_job={'metrics':{'generation_tps':99}});store.save(self.record)
        harness.ACTIVE['p_demo']+=1
        try:
            with patch('ai_agent.choki.engine.bridge.bridge') as bridge:
                self.assertNotIn('job',harness.status('p_demo'));bridge.call.assert_not_called()
        finally:del harness.ACTIVE['p_demo']

    def test_repository_name_does_not_install_an_application_profile(self):
        self.record['repository']='hushmind3/project-zero'
        harness.configure(self.record,False);store.save(self.record)
        data=runtime.invoke(self.record,{'path':'/compose'})
        self.assertEqual(json.loads(base64.b64decode(data['body']))['text'],'ORIGINAL')
        schema=runtime.invoke(self.record,{'path':'/openapi.json'})
        self.assertNotIn('/api/admin/platform/workspace',json.loads(base64.b64decode(schema['body']))['paths'])

    def test_switch_off_uses_original_provider(self):
        harness.configure(self.record,False);store.save(self.record)
        data=runtime.invoke(self.record,{'path':'/compose'})
        self.assertEqual(json.loads(base64.b64decode(data['body']))['text'],'ORIGINAL')

    def test_another_users_active_agent_is_not_started_or_stopped(self):
        fake=Mock();fake.busy_reason.return_value='user task'
        cancelled=threading.Event();cancelled.set()
        with patch('ai_agent.choki.engine.bridge.bridge',fake),self.assertRaisesRegex(ValueError,'중단'):
            harness.execute('p_demo',{'system':'system','user':'request'},cancelled)
        fake.call.assert_not_called()
        self.assertFalse(harness.ACTIVE)

    def test_control_cannot_answer_another_sessions_approval(self):
        self.record['harness'].update(session_id='owned',state='complete');store.save(self.record)
        fake=Mock();fake.call.return_value={'job':{'session_id':'other','state':'running','approval':{'kind':'tool','detail':'private'}}}
        with patch('ai_agent.choki.engine.bridge.bridge',fake),self.assertRaisesRegex(ValueError,'실행 중'):
            harness.control('p_demo',{'action':'answer','allow':True})
        self.assertEqual([c.args[0] for c in fake.call.call_args_list],['status'])


if __name__=='__main__':unittest.main()
