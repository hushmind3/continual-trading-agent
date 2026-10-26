"""Opt-in real-model desktop and browser checks; never run during ordinary test discovery."""
import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import unittest
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from ai_agent.choki.engine.bridge import WorkerBridge

@unittest.skipUnless(os.environ.get('HERMES_LIVE_TOOLS') == '1', 'Explicit live desktop/browser verification only')
class HermesLiveTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        query = urllib.parse.urlencode({'operation':'ai_agent/choki/settings','payload':'{}'})
        cfg = json.load(urllib.request.urlopen('http://127.0.0.1:8766/api?' + query))
        cls.folder = ROOT / 'runtime/ai_agent/choki/verification/interaction'
        cls.folder.mkdir(parents=True, exist_ok=True)
        cls.bridge = WorkerBridge(cls.folder / ('state-' + uuid.uuid4().hex[:8]))
        cls.addClassCleanup(cls.bridge.close)
        cls.bridge.call('settings/save', {'base_url':cfg['base_url'], 'model':cfg['model'], 'local_model':'',
            'workspace':str(cls.folder), 'max_iterations':20, 'toolsets':['computer_use']})
        # Own the model during the live check; a UI model reload must not strand
        # this worker on the old ephemeral server port.
        if cfg.get('local_model'):
            req=urllib.request.Request('http://127.0.0.1:8766/api',data=json.dumps({
                'operation':'ai_agent/choki/model/unload','payload':{}}).encode(),headers={'Content-Type':'application/json'})
            urllib.request.urlopen(req).close()
            cls.bridge.call('model/load', {'path':cfg['local_model']})
            for _ in range(40):
                if cls.bridge.call('status')['local_model']['state']=='ready':break
                time.sleep(.5)
        cls.model = cfg['model']
        cls.desktop_result = cls.folder / ('desktop-' + uuid.uuid4().hex[:8] + '.txt')
        compiler = Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
        shutil.copyfile(ROOT / 'development/tests/fixtures/hermes_desktop.cs', cls.folder / 'DesktopFixture.cs')
        subprocess.run([str(compiler), '/nologo', '/target:winexe', '/reference:System.Windows.Forms.dll',
            '/out:hermes-desktop-fixture.exe', 'DesktopFixture.cs'], cwd=cls.folder, check=True, capture_output=True)
        cls.desktop = subprocess.Popen([str(cls.folder / 'hermes-desktop-fixture.exe'), str(cls.desktop_result)], cwd=cls.folder)
        cls.web_result = ''
        html = """<!doctype html><html><head><title>Hermes Browser Check</title></head><body><h1>Hermes Browser Check</h1>
<label for="entry">Test input</label><input id="entry"><button onclick="document.getElementById('result').textContent='Confirmed: '+document.getElementById('entry').value;fetch('/result',{method:'POST',body:document.getElementById('entry').value})">Confirm</button><p id="result" role="status">Waiting</p></body></html>"""
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(html.encode())
            def do_POST(self):
                cls.web_result = self.rfile.read(int(self.headers.get('Content-Length',0))).decode()
                self.send_response(200);self.end_headers();self.wfile.write(b'ok')
        cls.web = http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=cls.web.serve_forever,daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.bridge.close()
        cls.web.shutdown();cls.web.server_close()
        if cls.desktop.poll() is None:cls.desktop.terminate();cls.desktop.wait(timeout=5)

    def run_task(self, message, toolset, label, timeout=180):
        self.bridge.call('settings/save', {'toolsets':[toolset]})
        state = self.bridge.call('chat', {'message':message})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.bridge.call('status')
            job = state['job']
            approval = job.get('approval')
            if approval:
                detail = approval['detail'].lower()
                calls = [e['detail'] for e in job['events'] if e['name']=='tool_start']
                last_call = calls[-1] if calls else ''
                allowed = approval['kind']=='tool' and 'computer_use' in detail and 'hermes-desktop-fixture.exe' in last_call
                self.bridge.call('answer', {'allow':allowed})
                print('SCOPED_APPROVAL',label,allowed,flush=True)
            if job['state'] not in ('starting','running','stopping'):break
            time.sleep(.5)
        else:
            self.bridge.call('stop')
            self.fail(label+' exceeded the bounded live check')
        (self.folder / (label+'-result.json')).write_text(json.dumps({'model':self.model,'status':state},ensure_ascii=False,indent=2),encoding='utf-8')
        print(label,job['state'],job['text'][-500:],job['error'],flush=True)
        print('TOOLS',[e['detail'][:280] for e in job['events'] if e['name']=='tool_start'],flush=True)
        self.assertEqual(job['state'],'complete',job['error'])
        return job

    def test_01_desktop_click_type_read(self):
        job=self.run_task(
            f"Use ONLY computer_use to interact with the existing hermes-desktop-fixture.exe window titled Hermes Interaction Check (pid {self.desktop.pid}). "
            "Do not touch any other app. Capture mode='ax' to read its controls (this model has no vision projector). "
            "On every input action explicitly pass app='hermes-desktop-fixture.exe'. Click Test input, type exactly DESKTOP_HERMES_OK, "
            "Do not repeatedly recapture the input value; click Confirm immediately after typing, then capture mode='ax' and read the result. Do not use terminal or files. Reply briefly in Korean.",
            'computer_use','desktop')
        self.assertTrue(self.desktop_result.is_file(), 'The actual desktop button did not write its result')
        self.assertEqual(self.desktop_result.read_text(encoding='utf-8-sig'),'DESKTOP_HERMES_OK')
        messages=self.bridge.call('session',{'id':job['session_id']})['messages']
        self.assertTrue(any('Confirmed: DESKTOP_HERMES_OK' in str(m.get('content'))
                            for m in messages if m.get('role')=='tool'),
                        'The model must read the actual accessible confirmation after clicking')
        events=' '.join(e['detail'] for e in job['events'] if e['name']=='tool_start')
        self.assertIn('computer_use',events);self.assertIn('click',events)

    def test_02_browser_navigate_type_click_read(self):
        token='BROWSER_HERMES_OK'
        job=self.run_task(
            f"Use browser_navigate to open http://127.0.0.1:{self.web.server_port}/. This is a local test page we own. "
            f"Read its snapshot, use browser_type to fill the Test input field with exactly {token}, use browser_click on Confirm, "
            "then browser_snapshot to read Confirmed. Only use browser_navigate, browser_type, browser_click, browser_snapshot. "
            "Do not use browser_console, JavaScript, terminal, files or computer_use. Reply briefly in Korean.",
            'browser','browser')
        self.assertEqual(self.web_result,token, 'The actual local page did not receive the click/input result')
        events=' '.join(e['detail'] for e in job['events'] if e['name']=='tool_start')
        for name in ('browser_navigate','browser_type','browser_click','browser_snapshot'):self.assertIn(name,events)

if __name__=='__main__':unittest.main()
