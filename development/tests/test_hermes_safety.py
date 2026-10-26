import json
from pathlib import Path
import sys
import tempfile
import threading
from dataclasses import dataclass
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from ai_agent.choki.chat.read_only import bind
from ai_agent.choki.engine.bridge import WorkerBridge


class ReadOnlyTests(unittest.TestCase):
    def test_only_workspace_reads_reach_executor_and_mixed_batch_runs_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            agent=SimpleNamespace(_execute_tool_calls=Mock())
            execute=agent._execute_tool_calls;bind(agent,temporary)
            def call(name,path='.'):
                return {'function':{'name':name,'arguments':json.dumps({'path':path,'command':'anything'})}}
            agent._execute_tool_calls({'tool_calls':[call('read_file'),call('search_files')]},[], 'task')
            execute.assert_called_once();execute.reset_mock()
            for name in ('write_file','patch','terminal','execute_code','delegate_task','tool_call','computer_use','mcp_unknown'):
                with self.subTest(name=name),self.assertRaises(PermissionError):
                    agent._execute_tool_calls({'tool_calls':[call('read_file'),call(name)]})
            execute.assert_not_called()
            with self.assertRaises(PermissionError):agent._execute_tool_calls({'tool_calls':[call('read_file','../outside')]})


class RestartTests(unittest.TestCase):
    def test_idle_bridge_check_does_not_start_worker(self):
        bridge=WorkerBridge()
        with patch.object(bridge,'_start') as start:
            self.assertEqual(bridge.busy_reason(),'');start.assert_not_called()

    def test_running_or_unreachable_worker_blocks_restart(self):
        for state in ('starting','running','stopping'):
            bridge=WorkerBridge();bridge.process=Mock();bridge.process.poll.return_value=None
            with patch.object(bridge,'call',return_value={'job':{'state':state}}),self.assertRaises(RuntimeError):bridge.reserve_restart()
            self.assertFalse(bridge.restarting)
        bridge=WorkerBridge();bridge.process=Mock();bridge.process.poll.return_value=None
        with patch.object(bridge,'call',side_effect=RuntimeError('timeout')):
            self.assertIn('확인 실패',bridge.busy_reason())

    def test_reserved_restart_rejects_new_work_before_starting_process(self):
        bridge=WorkerBridge();bridge.reserve_restart()
        with patch.object(bridge,'_start') as start,self.assertRaises(RuntimeError):bridge.call('chat',{'message':'work'})
        start.assert_not_called();bridge.cancel_restart()

    def test_host_restart_blockers_include_hermes_without_finance_imports(self):
        import platform_modules
        entry=SimpleNamespace(busy_reason=lambda:'Hermes busy')
        with patch.object(platform_modules,'registrations',return_value=[({'id':'hermes'},entry)]):
            self.assertEqual(platform_modules.busy_reasons(),['Hermes busy'])


class AutonomousCompletionTests(unittest.TestCase):
    def test_incomplete_native_turn_never_reaches_goal_or_loop_judge(self):
        from ai_agent.choki.chat.autonomy import run
        @dataclass
        class State:
            goal:str='goal'
            status:str='active'
            paused_reason:str=''
        class Manager:
            def __init__(self,*args):self.state=None
            def is_active(self):return bool(self.state and self.state.status=='active')
            def set(self,*args,**kwargs):self.state=State()
            def pause(self,reason):self.state.status='paused';self.state.paused_reason=reason
            def is_waiting(self):return False
            def fire_tick(self):return 'tick'
            def evaluate_after_turn(self,*args):raise AssertionError('Incomplete turn was judged')
            complete_tick=evaluate_after_turn
        modules={'hermes_cli.goals':SimpleNamespace(GoalManager=Manager,goal_kick_prompt=lambda *args:'goal',last_user_message_content=lambda rows:'goal'),
            'hermes_cli.loops':SimpleNamespace(LoopManager=Manager)}
        for mode in ('goal','loop'):
            for outcome in ({'completed':False},{'failed':True}):
                worker=SimpleNamespace(native_config=lambda:{},write_config=Mock(),lock=threading.RLock(),job={},stopping=False,event=Mock())
                agent=SimpleNamespace(run_conversation=Mock(return_value=outcome))
                with patch.dict(sys.modules,modules):result=run(worker,agent,{'model':'fixture','base_url':'http://localhost'},'session','goal',[],{'mode':mode})
                self.assertEqual(result,outcome);self.assertEqual(worker.job['autonomy']['status'],'paused')
                agent.run_conversation.assert_called_once()


class ModelStampTests(unittest.TestCase):
    def test_registered_weight_changes_are_detected_without_recursive_walk(self):
        import web_api
        from stockrl.management.diagnostics_logs_code_apply import handlers
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);model=root/'experts/market/a';model.mkdir(parents=True)
            (model/'MODEL.json').write_text(json.dumps({'weight_asset':{'file':'market/a/weights.bin'}}))
            weight=model/'weights.bin';weight.write_bytes(b'a')
            catalog={'experts':{'a':{'package':{'file':'market/a/MODEL.json'}}}}
            with patch.object(handlers,'MODEL_DIR',root),patch('stockrl.expert_registry.read_catalog',return_value=catalog),patch.object(Path,'rglob',side_effect=AssertionError('recursive scan')):
                before=handlers.model_stamp();weight.unlink();after=handlers.model_stamp()
            self.assertNotEqual(before,after)


if __name__=='__main__':unittest.main()
