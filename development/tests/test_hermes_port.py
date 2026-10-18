r"""Exercise the copied engine with protocol fixtures, not a real model or broker.

Run: .venv\Scripts\python.exe -X utf8 -m unittest development.tests.test_hermes_port -v
"""
from __future__ import annotations
import http.server
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from ai_agent.Hermes.engine.bridge import WorkerBridge


class ModelFixture(http.server.BaseHTTPRequestHandler):
    slow = threading.Event()
    calls = []
    forced_tools = []

    def log_message(self, *args): pass

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'data': [{'id': 'port-fixture'}], 'object': 'list'}).encode())

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.calls.append(body)
        if any('PORT_STOP' in str(m.get('content')) for m in body.get('messages', [])):
            self.slow.set()
            time.sleep(3)
        names = [t.get('function', {}).get('name') for t in body.get('tools', [])]
        mcp_echo = next((name for name in names if name and 'echo' in name and 'port_fixture' in name), None)
        tool_results = [m for m in body.get('messages', []) if m.get('role') == 'tool']
        is_mcp = any('Call the port_fixture' in str(m.get('content')) for m in body.get('messages', []))
        for row in tool_results:
            try: found = json.loads(row.get('content') or '{}').get('tools', {})
            except (ValueError, AttributeError): continue
            mcp_echo = next((name for name in found if 'echo' in name and 'port_fixture' in name), mcp_echo)
        described = any(call.get('function', {}).get('name') == 'tool_describe'
                        for row in body.get('messages', []) for call in row.get('tool_calls', []))
        if any('PORT_WRITE_ATTACK' in str(m.get('content')) for m in body.get('messages', [])):
            self.forced_tools.append('write_file')
            message={'role':'assistant','content':None,'tool_calls':[{'id':'blocked-write','type':'function','function':{'name':'write_file','arguments':json.dumps({'path':'hermes_port_result.txt','content':'changed'})}}]}
            finish='tool_calls'
        elif any('PORT_SHELL' in str(m.get('content')) for m in body.get('messages', [])):
            self.forced_tools.append('terminal')
            message={'role':'assistant','content':None,'tool_calls':[{'id':'blocked-shell','type':'function','function':{'name':'terminal','arguments':json.dumps({'command':'printf blocked > blocked_shell.txt'})}}]}
            finish='tool_calls'
        elif is_mcp and not mcp_echo and not tool_results and 'tool_search' in names:
            message = {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'port_search', 'type': 'function', 'function': {
                'name': 'tool_search', 'arguments': json.dumps({'queries': ['port_fixture echo']})}}]}
            finish = 'tool_calls'
        elif is_mcp and mcp_echo and not described and 'tool_describe' in names:
            message = {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'port_describe', 'type': 'function', 'function': {
                'name': 'tool_describe', 'arguments': json.dumps({'names': [mcp_echo]})}}]}
            finish = 'tool_calls'
        elif mcp_echo and not any('PORT_MCP_ECHO' in str(m.get('content')) for m in tool_results):
            message = {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'port_echo', 'type': 'function', 'function': {
                'name': 'tool_call', 'arguments': json.dumps({'calls': [{'name': mcp_echo, 'arguments': {'text': 'PORT_MCP_ECHO'}}]})}}]}
            finish = 'tool_calls'
        elif 'write_file' in names and not any(m.get('role') == 'tool' for m in body.get('messages', [])):
            message = {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'port_write', 'type': 'function', 'function': {
                'name': 'write_file', 'arguments': json.dumps({'path': 'hermes_port_result.txt', 'content': 'copied engine executed this tool'})}}]}
            finish = 'tool_calls'
        else:
            message = {'role': 'assistant', 'content': 'PORT_DONE'}
            finish = 'stop'
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream' if body.get('stream') else 'application/json')
            self.end_headers()
            if body.get('stream'):
                for delta, reason in [(message, None), ({}, finish)]:
                    for index, tool in enumerate(delta.get('tool_calls', [])): tool['index'] = index
                    self.wfile.write(('data: ' + json.dumps({'id': 'port', 'object': 'chat.completion.chunk', 'model': 'port-fixture',
                        'created': 1, 'choices': [{'index': 0, 'delta': delta, 'finish_reason': reason}]}) + '\n\n').encode())
                self.wfile.write(('data: '+json.dumps({'id':'port','choices':[],'usage':{'prompt_tokens':128,'completion_tokens':16,'total_tokens':144}})+'\n\n').encode())
                self.wfile.write(b'data: [DONE]\n\n')
            else:
                self.wfile.write(json.dumps({'id': 'port', 'object': 'chat.completion', 'model': 'port-fixture', 'created': 1,
                    'choices': [{'index': 0, 'message': message, 'finish_reason': finish}], 'usage': {'prompt_tokens':128,'completion_tokens':16,'total_tokens':144}}).encode())
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError): pass


@unittest.skipUnless((ROOT / '.venv/hermes/Scripts/python.exe').exists(), 'Hermes Python environment is not installed')
class HermesPortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        checks = ROOT / 'runtime/ai_agent/Hermes/verification/port'
        checks.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix='run-', dir=checks)
        cls.addClassCleanup(cls.temp.cleanup)
        cls.folder = Path(cls.temp.name)
        cls.workspace = cls.folder / 'workspace'
        cls.workspace.mkdir()
        cls.bridge = WorkerBridge(cls.folder / 'state')
        cls.addClassCleanup(cls.bridge.close)
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), ModelFixture)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)
        cls.base = f'http://127.0.0.1:{cls.server.server_port}/v1'
        cls.bridge.call('settings/save', {'base_url': cls.base, 'model': 'port-fixture',
            'workspace': str(cls.workspace), 'max_iterations': 5, 'toolsets': ['file', 'skills']})

    def test_08_read_only_rejects_model_write_and_terminal_calls(self):
        original=self.workspace/'hermes_port_result.txt'
        original.write_text('keep',encoding='utf8')
        self.bridge.call('settings/save',{'read_only':False})
        try:
            for prompt,tool in (('PORT_WRITE_ATTACK','write_file'),('PORT_SHELL','terminal')):
                self.bridge.call('chat',{'message':prompt,'read_only':True})
                state=self.wait_job()
                self.assertEqual(original.read_text(encoding='utf8'),'keep')
                self.assertFalse((self.workspace/'blocked_shell.txt').exists())
                self.assertIn(tool,ModelFixture.forced_tools)
                self.assertNotIn(tool,[entry.get('function',{}).get('name') for entry in ModelFixture.calls[-1].get('tools',[])])
                self.assertTrue(state.get('error') or any(event['name']=='permission_denied' for event in state['events']))
        finally:self.bridge.call('settings/save',{'read_only':False})

    def wait_job(self, timeout=35):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            status = self.bridge.call('status')['job']
            if status['state'] not in ('starting', 'running', 'stopping'): return status
            time.sleep(.15)
        self.fail('Agent did not finish in the bounded fixture timeout')

    def test_01_native_chat_tool_and_persistent_session(self):
        saved=self.bridge.call('settings/save',{'system_prompt':'PORT_SYSTEM_PROMPT: answer concisely in Korean.'})
        self.assertIn('PORT_SYSTEM_PROMPT',saved['system_prompt'])
        status = self.bridge.call('chat', {'message': 'PORT_WRITE: write hermes_port_result.txt using write_file.'})
        session_id = status['job']['session_id']
        result = self.wait_job()
        self.assertEqual(result['state'], 'complete', result.get('error'))
        self.assertTrue(result['text'].startswith('PORT_DONE'), result['text'])
        self.assertTrue(any('PORT_SYSTEM_PROMPT' in str(message.get('content')) for call in ModelFixture.calls for message in call.get('messages',[]) if message.get('role')=='system'))
        self.bridge.call('settings/save',{'system_prompt':''})
        self.assertGreater(result['metrics']['input_tokens'], 0)
        self.assertGreater(result['metrics']['output_tokens'], 0)
        self.assertGreater(result['metrics']['api_calls'], 0)
        self.assertGreaterEqual(result['metrics']['elapsed_seconds'], 0)
        output = self.workspace / 'hermes_port_result.txt'
        self.assertTrue(output.is_file(), json.dumps(result, ensure_ascii=False))
        self.assertEqual(output.read_text(), 'copied engine executed this tool')
        history = self.bridge.call('session', {'id': session_id})['messages']
        self.assertIn('tool', [row['role'] for row in history])
        engine = self.bridge.call('engine/info')
        self.assertTrue(all(Path(path).is_relative_to(Path(engine['root'])) for path in engine['modules'].values()))
        self.bridge.close()
        reopened = self.bridge.call('session', {'id': session_id})
        self.assertEqual(reopened['messages'], history)
        self.bridge.call('chat', {'session_id': session_id, 'message': 'Continue the previous session.'})
        self.assertEqual(self.wait_job()['state'], 'complete')

    def test_02_native_skills(self):
        first = self.bridge.call('session/create', {'title': '새 대화'})['session']
        second = self.bridge.call('session/create', {'title': '새 대화'})['session']
        self.assertNotEqual(first['id'], second['id'])
        self.assertNotEqual(first['title'], second['title'])
        catalog = self.bridge.call('skills')
        self.assertGreater(len(catalog['skills']), 0)
        view = self.bridge.call('skill', {'name': 'computer-use'})
        self.assertTrue(view['success'])
        self.assertIn('computer', view['content'].lower())

    def test_10_native_context_and_unrestricted_local_request(self):
        marker = self.workspace / 'AGENTS.md'
        marker.write_text('NATIVE_CONTEXT_INJECTION_MARKER: use the fixture workspace only.', encoding='utf-8')
        start = len(ModelFixture.calls)
        try:
            self.bridge.call('chat', {'message': 'Create a greeting in the fixture workspace.'})
            job = self.wait_job()
            self.assertEqual(job['state'], 'complete', job.get('error'))
            calls = ModelFixture.calls[start:]
            self.assertTrue(calls)
            self.assertTrue(any('NATIVE_CONTEXT_INJECTION_MARKER' in json.dumps(call.get('messages'), ensure_ascii=False) for call in calls))
            self.assertTrue(all(call.get('max_tokens') != 2048 for call in calls))
            self.assertTrue(all(call.get('reasoning') != {'enabled': False} for call in calls))
        finally:
            marker.unlink(missing_ok=True)

    def test_11_original_review_finishes_before_worker_releases_agent(self):
        config = self.folder / 'state' / 'config.yaml'
        original = config.read_text(encoding='utf-8')
        configured=original.replace('skills:\n','skills:\n  creation_nudge_interval: 1\n',1) if 'skills:\n' in original else original+'\nskills:\n  creation_nudge_interval: 1\n'
        config.write_text(configured, encoding='utf-8')
        try:
            self.bridge.call('chat', {'message': 'Create a greeting in the fixture workspace.'})
            job = self.wait_job()
            self.assertEqual(job['state'], 'complete', job.get('error'))
            self.assertTrue(any(event['name'] == 'status' and '검토 중' in event['detail'] for event in job['events']))
        finally:
            config.write_text(original, encoding='utf-8')

    def test_03_settings_validation_and_model_discovery(self):
        self.assertEqual(self.bridge.call('models')['models'], [{'id': 'port-fixture'}])
        with self.assertRaisesRegex(RuntimeError, '존재하지'):
            self.bridge.call('settings/save', {'workspace': str(self.folder / 'missing')})
        self.assertEqual(self.bridge.call('settings')['workspace'], str(self.workspace))

    def test_04_native_mcp_stdio_discovery(self):
        script = self.folder / 'mcp_fixture.py'
        script.write_text('''import json,sys
for line in sys.stdin:
 r=json.loads(line)
 if 'id' not in r: continue
 method=r.get('method')
 result={'protocolVersion':'2025-03-26','capabilities':{'tools':{}},'serverInfo':{'name':'fixture','version':'1'}} if method=='initialize' else {'tools':[{'name':'echo','description':'Echo fixture','inputSchema':{'type':'object','properties':{'text':{'type':'string'}}}}]} if method=='tools/list' else {'content':[{'type':'text','text':r.get('params',{}).get('arguments',{}).get('text','')}]} if method=='tools/call' else {}
 print(json.dumps({'jsonrpc':'2.0','id':r['id'],'result':result}),flush=True)
''', encoding='utf-8')
        settings = {'port_fixture': {'command': str(ROOT / 'modules/hermes/.venv/Scripts/python.exe'), 'args': ['-I', '-X', 'utf8', str(script)]}}
        self.bridge.call('mcp/save', {'servers': settings})
        result = self.bridge.call('mcp/connect')
        self.assertEqual(result['servers'], settings)
        self.assertTrue(result['status'])
        self.assertTrue(result['status'][0]['connected'])
        self.assertEqual(result['status'][0]['tools'], 1)
        self.assertIn('echo', json.dumps(result))
        chat = self.bridge.call('chat', {'message': 'Call the port_fixture echo tool with PORT_MCP_ECHO.'})
        self.assertEqual(self.wait_job()['state'], 'complete')
        messages = self.bridge.call('session', {'id': chat['job']['session_id']})['messages']
        self.assertTrue(any('PORT_MCP_ECHO' in str(row.get('content')) for row in messages if row['role'] == 'tool'),
            json.dumps({'messages': messages, 'tools': [[t.get('function', {}).get('name') for t in call.get('tools', [])] for call in ModelFixture.calls[-4:]]}, ensure_ascii=False)[-5500:])
        self.bridge.call('mcp/save', {'servers': {}})

    def test_05_stop(self):
        ModelFixture.slow.clear()
        self.bridge.call('chat', {'message': 'PORT_STOP wait for cancellation'})
        self.assertTrue(ModelFixture.slow.wait(timeout=15))
        result = self.bridge.call('stop')
        self.assertEqual(result['job']['state'], 'stopping')
        self.assertEqual(self.wait_job()['state'], 'stopped')

    def test_06_catalog_install_and_skills_edit_persist(self):
        catalog = self.bridge.call('mcp/catalog')
        self.assertEqual(len(catalog['entries']), 65)
        self.assertTrue(all(row['description'] for row in catalog['entries']))
        with self.assertRaisesRegex(RuntimeError, '카탈로그'):
            self.bridge.call('mcp/catalog/install', {'name': 'not-a-real-catalog-entry'})
        self.bridge.call('mcp/catalog/install', {'name': 'alltrails'})
        end = time.monotonic() + 8
        while time.monotonic() < end:
            install = self.bridge.call('mcp/catalog')['installation']
            if install['state'] != 'running': break
            time.sleep(.1)
        self.assertEqual(install['state'], 'complete', install)
        installed = self.bridge.call('mcp')['servers']['alltrails']
        self.assertEqual(installed['url'], 'https://www.alltrails.com/mcp')
        self.bridge.call('mcp/save', {'servers': {}})
        off = self.bridge.call('skill/toggle', {'name': 'arxiv', 'enabled': False})
        self.assertFalse(next(r for r in off['skills'] if r['name'] == 'arxiv')['enabled'])
        self.bridge.close()
        self.assertFalse(next(r for r in self.bridge.call('skills')['skills'] if r['name'] == 'arxiv')['enabled'])
        self.bridge.call('skill/toggle', {'name': 'arxiv', 'enabled': True})
        content = '---\nname: port-check\ndescription: Fixture instructions\n---\n# Check\nRead a local file when asked.\n'
        created = self.bridge.call('skill/save', {'name': 'port-check', 'content': content, 'create': True})
        self.assertTrue(created['success'], created)
        edited = content.replace('Read a local file', 'Summarize a local file')
        self.bridge.call('skill/save', {'name': 'port-check', 'content': edited})
        self.assertEqual(self.bridge.call('skill/content', {'name': 'port-check'})['content'], edited)

    def test_08_platform_browser_tool_is_exposed_to_model(self):
        prior = self.bridge.call('settings')['toolsets']
        try:
            self.bridge.call('settings/save', {'toolsets': ['file', 'computer_use']})
            before = len(ModelFixture.calls)
            self.bridge.call('chat', {'message': 'PORT_WRITE: write a local file.'})
            result = self.wait_job()
            self.assertEqual(result['state'], 'complete', result.get('error'))
            names = {t.get('function', {}).get('name') for call in ModelFixture.calls[before:] for t in call.get('tools', [])}
            self.assertIn('desktop_browser', names)
        finally:
            self.bridge.call('settings/save', {'toolsets': prior})

    def test_07_native_loop_stop_resume_and_session_reopen(self):
        status = self.bridge.call('chat', {'message': 'PORT_LOOP: report progress on each wakeup.',
            'mode': 'loop', 'times': 2, 'interval_seconds': 5})
        sid = status['job']['session_id']
        end = time.monotonic() + 15
        while time.monotonic() < end:
            state = self.bridge.call('status')['job']
            if state.get('autonomy', {}).get('ticks_fired') == 1 and any(r['name'] == 'autonomy_decision' for r in state['events']): break
            time.sleep(.1)
        self.assertEqual(state['state'], 'running', state)
        self.assertEqual(state['autonomy']['mode'], 'loop')
        self.bridge.call('stop')
        self.assertEqual(self.wait_job()['state'], 'stopped')
        self.assertEqual(self.bridge.call('autonomy', {'id': sid})['loop']['status'], 'paused')
        self.bridge.close()
        self.assertEqual(self.bridge.call('autonomy', {'id': sid})['loop']['ticks_fired'], 1)
        self.bridge.call('chat', {'session_id': sid, 'message': '/loop resume'})
        result = self.wait_job(timeout=30)
        self.assertEqual(result['state'], 'complete', result)
        self.assertEqual(result['autonomy']['ticks_fired'], 2)
        self.assertEqual(result['autonomy']['status'], 'done')


    def test_09_session_rename_persists_without_replacing_history(self):
        session=self.bridge.call('session/create',{'title':'이름 변경 전'})['session']
        self.bridge.call('chat',{'session_id':session['id'],'message':'Create a greeting in the fixture workspace.'})
        self.assertEqual(self.wait_job()['state'],'complete')
        history=self.bridge.call('session',{'id':session['id']})['messages']
        self.assertTrue(history)
        self.bridge.call('session/rename',{'id':session['id'],'title':'  오류   점검 기록  '})
        renamed=self.bridge.call('session',{'id':session['id']})
        self.assertEqual(renamed['session']['title'],'오류 점검 기록')
        self.assertEqual(renamed['messages'],history)
        with self.assertRaises(RuntimeError):self.bridge.call('session/rename',{'id':session['id'],'title':' '})
        with self.assertRaises(RuntimeError):self.bridge.call('session/rename',{'id':'missing-session','title':'제목'})
        self.bridge.close()
        self.assertEqual(self.bridge.call('session',{'id':session['id']})['session']['title'],'오류 점검 기록')

if __name__ == '__main__': unittest.main()
