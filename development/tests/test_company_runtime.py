"""Company tabs observe/control the same native run; removal cannot race it."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
import uuid
import io
import json
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import harness
from ai_agent.choki.chat import company
from ai_agent.choki.engine.runtime_policy import auxiliary_thinking

class NativeRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.record={'id':'demo','stage':'ready','harness':{'enabled':True},'workspace_ui':{'native':{'token':'internal'}}}
        self.sid=uuid.uuid5(uuid.NAMESPACE_URL,'platform-company:demo').hex
        self.bridge=Mock();self.bridge.process.poll.return_value=None
        self.bridge.call.return_value={'job':{'session_id':self.sid,'state':'running','company_id':'demo','metrics':{'output_tokens':123}}}
        p=patch('ai_agent.choki.engine.bridge.bridge',self.bridge);p.start();self.addCleanup(p.stop)
        p=patch.object(harness.store,'read',return_value=self.record);p.start();self.addCleanup(p.stop)
    def test_tabs_share_native_measurements_and_owned_stop(self):
        state=harness.status('demo');self.assertTrue(state['native']);self.assertEqual(state['job']['metrics']['output_tokens'],123)
        self.assertTrue(harness.control('demo',{'action':'stop'})['requested'])
        self.bridge.call.assert_called_with('stop',{'session_id':self.sid})
        self.assertIn('Hermes',harness.busy_reason())
    def test_other_native_job_is_not_exposed_or_stopped(self):
        self.bridge.call.return_value={'job':{'session_id':'another','state':'running'}}
        self.assertIsNone(harness.status('demo')['job']);self.assertFalse(harness.control('demo',{'action':'stop'})['requested'])
        self.assertFalse(any(c.args[0]=='stop' for c in self.bridge.call.call_args_list))
    def test_no_pending_question_cannot_receive_an_answer(self):
        with self.assertRaises(ValueError):harness.control('demo',{'action':'answer','allow':True})

    def test_company_default_does_not_replace_explicit_native_workspace(self):
        worker=Mock();cfg={'workspace':'platform-default','manager_staff_id':'staff-test','staff_registry':[{'id':'staff-test','name':'총괄','default_prompt':'작업을 조율합니다.'}]}
        with patch.object(company,'links',return_value={self.sid:{'workspace':'company-default'}}):
            company.prepare(worker,cfg,self.sid)
            self.assertEqual(cfg['workspace'],'company-default')
            selected=Path(__file__).resolve().parent
            company.prepare(worker,cfg,self.sid,str(selected))
            self.assertEqual(cfg['workspace'],str(selected))

    def test_company_validation_error_is_actionable_without_capability_leak(self):
        worker=Mock();worker.company_link={'id':'demo','url':'http://127.0.0.1/api','token':'private-capability'}
        worker.job={'session_id':self.sid};worker.agent=None
        error=HTTPError(worker.company_link['url'],400,'Bad Request',{},io.BytesIO(b'{"detail":"Unknown job; private-capability"}'))
        with patch.object(company,'urlopen',side_effect=error):
            result=json.loads(company.execute({'action':'finish','job_id':'invented'},worker=worker))
        self.assertIn('Unknown job',result['detail'])
        self.assertNotIn('private-capability',json.dumps(result))

    def test_success_text_cannot_be_misfiled_as_error(self):
        worker=Mock();worker.company_link={'id':'demo'};worker.agent=None
        with patch.object(company,'urlopen') as send:
            result=json.loads(company.execute({'action':'finish','job_id':'real','error':'12 tests passed'},worker=worker))
        self.assertIn('action=fail',result['error']);send.assert_not_called()
        self.assertNotIn('error',company.SCHEMA['parameters']['properties'])

    def test_success_and_failure_are_explicit_record_actions(self):
        worker=Mock();worker.company_link={'id':'demo','url':'http://127.0.0.1/api','token':'internal'}
        worker.agent=None;worker.job={'session_id':self.sid}
        with patch.object(company,'urlopen',side_effect=lambda *a,**k:io.BytesIO(b'{"ok":true}')) as send:
            company.execute({'action':'finish','job_id':'real','body':'12 tests passed'},worker=worker)
            success=json.loads(send.call_args.args[0].data)['payload']['command']
            company.execute({'action':'fail','job_id':'real','body':'Compiler exited 1'},worker=worker)
            failure=json.loads(send.call_args.args[0].data)['payload']['command']
        self.assertNotIn('error',success)
        self.assertEqual(failure['action'],'finish');self.assertEqual(failure['error'],'Compiler exited 1')

class RecallAndGitTests(unittest.TestCase):
    def test_native_recall_only_uses_own_scope_and_bounds_context(self):
        worker=Mock();worker.job={'session_id':'own'};worker.company_visible_history=None
        worker.db.get_resume_conversations.return_value=([],[
            {'role':'user','content':'venture_a 견적서 가격 29000원','_row_id':1},
            {'role':'user','content':'venture_b 견적서 SECRET-B','_row_id':2},
            {'role':'tool','content':'venture_a 견적서 '+'x'*50000}])
        result=company.recall_transcript(worker,{'scope':'venture_a','terms':['견적서'],'items':[]})
        self.assertIn('29000',json.dumps(result,ensure_ascii=False));self.assertNotIn('SECRET-B',json.dumps(result))
        worker.db.get_resume_conversations.assert_called_once_with('own')
        self.assertLessEqual(len(json.dumps(result,ensure_ascii=False)),5000)
    def test_active_native_context_is_not_injected_twice(self):
        worker=Mock();worker.job={'session_id':'own'};worker.company_visible_history=None
        active={'role':'user','content':'견적서 현재 질문'}
        archived={'role':'user','content':'견적서 과거 결정','_row_id':1}
        worker.db.get_resume_conversations.return_value=([active],[archived,active])
        result=company.recall_transcript(worker,{'scope':'owner','terms':['견적서'],'items':[]})
        self.assertEqual([r['body'] for r in result['conversation']],['견적서 과거 결정'])
    def test_unsolicited_git_write_requires_existing_approval(self):
        worker=Mock();worker.approve.return_value='deny';agent=Mock();original=agent._execute_tool_calls
        company.bind_git_approval(worker,agent,'버튼을 수정해')
        message={'tool_calls':[{'function':{'name':'terminal','arguments':json.dumps({'command':'git -C project commit -m done'})}}]}
        with self.assertRaises(PermissionError):agent._execute_tool_calls(message)
        original.assert_not_called();worker.approve.assert_called_once()
        with self.assertRaises(PermissionError):agent._execute_tool_calls({'tool_calls':[{'function':{'name':'tool_call','arguments':{'calls':[{'name':'terminal','arguments':{'command':'git push origin main'}}]}}}]})
        original.assert_not_called()
        agent._execute_tool_calls({'tool_calls':[{'function':{'name':'terminal','arguments':{'command':'git status --short'}}}]})
        original.assert_called_once()

class AuxiliaryThinkingTests(unittest.TestCase):
    def setUp(self):
        self.cfg={'model':'local','base_url':'http://127.0.0.1:1000/v1','local_model':'local.gguf'}

    def test_local_choice_preserves_other_options_and_auto_restores_native(self):
        native={'auxiliary':{'compression':{'extra_body':{'keep':1,'chat_template_kwargs':{'enable_thinking':True,'keep':2}}},'goal_judge':{'max_tokens':500}}}
        self.assertTrue(auxiliary_thinking(native,self.cfg,{'thinking_mode':'off'}))
        self.assertFalse(native['auxiliary']['compression']['extra_body']['chat_template_kwargs']['enable_thinking'])
        self.assertEqual(native['auxiliary']['goal_judge']['max_tokens'],500)
        self.assertFalse(auxiliary_thinking(native,self.cfg,{'thinking_mode':'off'}))
        auxiliary_thinking(native,self.cfg,{'thinking_mode':'auto'})
        self.assertEqual(native,{'auxiliary':{'compression':{'extra_body':{'keep':1,'chat_template_kwargs':{'enable_thinking':True,'keep':2}}},'goal_judge':{'max_tokens':500}}})

    def test_separately_routed_aux_model_is_not_overridden(self):
        native={'auxiliary':{'compression':{'model':'different','provider':'other','extra_body':{'chat_template_kwargs':{'enable_thinking':True}}}}}
        auxiliary_thinking(native,self.cfg,{'thinking_mode':'off'})
        self.assertTrue(native['auxiliary']['compression']['extra_body']['chat_template_kwargs']['enable_thinking'])

    def test_external_model_does_not_receive_local_template_options(self):
        native={};self.cfg['local_model']=''
        self.assertFalse(auxiliary_thinking(native,self.cfg,{'thinking_mode':'off'}));self.assertEqual(native,{})

if __name__=='__main__':unittest.main()
