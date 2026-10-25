"""Real Node IPC and host startup without any business module or GPU dependency."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil
import threading
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from module_runtime import ModuleRuntime

def python_at(environment):
    return environment/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')

def site_at(environment):
    return environment/('Lib/site-packages' if sys.platform=='win32' else f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages')

class ModuleRuntimeTests(unittest.TestCase):
    def setUp(self):
        base=ROOT/'runtime/platform/module-verification';base.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=base);self.root=Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def test_failed_private_dependency_does_not_prevent_other_modules_loading(self):
        import platform_modules
        for name in ('available','broken'):
            folder=self.root/name;(folder/'backend').mkdir(parents=True)
            (folder/'module.json').write_text(json.dumps({'schema':1,'id':name,'group':{'id':name,'title':name},
                'backend':{'namespace':'isolated_test_'+name,'entry':'register'},'frontend':{'entry':'frontend/register.ts'}}),encoding='utf8')
            code="raise RuntimeError('private environment missing')" if name=='broken' else "VALUE='available'"
            (folder/'backend/register.py').write_text(code,encoding='utf8')
        platform_modules.registrations.cache_clear()
        try:
            with patch.object(platform_modules,'MODULES',self.root):
                entries={item['id']:entry for item,entry in platform_modules.registrations()}
                self.assertEqual(entries['available'].VALUE,'available')
                self.assertIn('private environment missing',entries['broken'].load_error)
        finally:platform_modules.registrations.cache_clear()

    def test_real_node_worker_uses_same_contract_without_a_python_backend(self):
        (self.root/'module.json').write_text(json.dumps({'id':'node_example','runtime':{
            'language':'node','protocol':'module-jsonl-v1','command':['node','{module}/worker.mjs'],
            'state':self.root.relative_to(ROOT).as_posix()}}),encoding='utf8')
        (self.root/'worker.mjs').write_text("""import {createInterface} from 'node:readline';
for await(const line of createInterface({input:process.stdin})){
 const request=JSON.parse(line);
 const result=request.operation==='describe'?{language:'node',pid:process.pid,cwd:process.cwd()}:request.payload;
 process.stdout.write(JSON.stringify({id:request.id,result})+'\\n');
 if(request.operation==='shutdown')break;
}
""",encoding='utf8')
        bridge=ModuleRuntime(self.root);self.addCleanup(bridge.close)
        description=bridge.call('describe',timeout=10)
        self.assertEqual(description['language'],'node')
        self.assertNotEqual(description['pid'],os.getpid())
        self.assertEqual(Path(description['cwd']),self.root)
        self.assertEqual(bridge.call('echo',{'value':'한글 결과'}),{'value':'한글 결과'})

    def runtime_fixture(self):
        (self.root/'module.json').write_text(json.dumps({'id':'lifecycle','runtime':{
            'command':['node','{module}/worker.mjs'],'state':self.root.relative_to(ROOT).as_posix()}}),encoding='utf8')
        return ModuleRuntime(self.root)

    def test_restart_reservation_blocks_new_requests_during_busy_check(self):
        bridge=self.runtime_fixture();self.addCleanup(bridge.close)
        checking=threading.Event();release=threading.Event();attempted=threading.Event()
        accepted=threading.Event();errors=[]
        def busy():
            checking.set()
            if not release.wait(5):raise RuntimeError('test busy check timeout')
            return ''
        def start():
            accepted.set()
            raise AssertionError('new request admitted during restart reservation')
        def reserve():
            try:bridge.reserve_restart()
            except Exception as exc:errors.append(exc)
        def request():
            attempted.set()
            try:bridge.call('request',{'method':'POST'})
            except RuntimeError:pass
            except Exception as exc:errors.append(exc)
        original=bridge.call
        def call(operation,payload=None,**kwargs):
            if operation=='hook':return None
            return original(operation,payload,**kwargs)
        with patch.object(bridge,'busy_reason',side_effect=busy),patch.object(bridge,'_start',side_effect=start),patch.object(bridge,'call',side_effect=call):
            reservation=threading.Thread(target=reserve);reservation.start()
            self.assertTrue(checking.wait(2))
            request_thread=threading.Thread(target=request);request_thread.start()
            try:
                self.assertTrue(attempted.wait(2))
                self.assertFalse(accepted.wait(.2))
            finally:
                release.set();reservation.join(5);request_thread.join(5)
            self.assertFalse(reservation.is_alive());self.assertFalse(request_thread.is_alive())
        self.assertEqual(errors,[])
        self.assertTrue(bridge.restarting)

    def test_shutdown_does_not_start_a_missing_or_just_exited_worker(self):
        for process in (None,Mock()):
            bridge=self.runtime_fixture();self.addCleanup(bridge.close)
            if process is not None:process.poll.return_value=0
            bridge.process=process
            with patch.object(bridge,'_start',side_effect=AssertionError('shutdown started a new worker')):
                self.assertTrue(bridge.call('shutdown'))

    def test_real_node_restart_can_be_cancelled_without_losing_ipc(self):
        bridge=self.runtime_fixture();self.addCleanup(bridge.close)
        (self.root/'worker.mjs').write_text("""import {createInterface} from 'node:readline';
for await(const line of createInterface({input:process.stdin})){
 const request=JSON.parse(line);
 const result=request.operation==='hook'?(request.payload.name==='busy'?[]:true):request.payload;
 process.stdout.write(JSON.stringify({id:request.id,result})+'\\n');
 if(request.operation==='shutdown')break;
}
""",encoding='utf8')
        self.assertEqual(bridge.call('echo',{'value':'분리 준비'}),{'value':'분리 준비'})
        process=bridge.process
        bridge.reserve_restart()
        with self.assertRaisesRegex(RuntimeError,'준비 중'):bridge.call('request',{'method':'POST'})
        bridge.cancel_restart()
        self.assertEqual(bridge.call('echo',{'value':'재연결'}),{'value':'재연결'})
        self.assertIs(bridge.process,process)
        bridge.close()
        self.assertIsNotNone(process.poll())

    def test_moved_environment_repairs_its_own_console_launchers(self):
        sys.path.insert(0,str(ROOT/'development/scripts'))
        from module_sources import install
        original=self.root/'original';original.mkdir();(original/'module.json').write_text('{"runtime":{}}')
        subprocess.run([sys.executable,'-m','venv',str(original/'.venv')],check=True,capture_output=True,timeout=30)
        site=site_at(original/'.venv')
        (site/'portable_probe.py').write_text('import sys,json\ndef main():print(json.dumps(sys.prefix,ensure_ascii=True))\n',encoding='utf8')
        info=site/'portable_probe-0.1.dist-info';info.mkdir()
        (info/'METADATA').write_text('Name: portable-probe\nVersion: 0.1\n',encoding='utf8')
        (info/'entry_points.txt').write_text('[console_scripts]\nportable-probe = portable_probe:main\n',encoding='utf8')
        install(original/'.venv')
        subprocess.run([str(python_at(original/'.venv')),'-I','-c','pass'],check=True,capture_output=True,timeout=20)
        moved=self.root/'moved';original.rename(moved)
        subprocess.run([str(python_at(moved/'.venv')),'-I','-c','pass'],check=True,capture_output=True,timeout=20)
        launcher=moved/'.venv'/('Scripts/portable-probe.exe' if sys.platform=='win32' else 'bin/portable-probe')
        result=subprocess.run([str(launcher)],check=True,capture_output=True,text=True,encoding='utf8',timeout=10)
        self.assertEqual(Path(json.loads(result.stdout.strip())),moved/'.venv')

    def test_minimal_host_boots_without_finance_rea_hermes_or_torch(self):
        empty=self.root/'modules';empty.mkdir()
        code="""import sys,json,asyncio,urllib.parse
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'backend'))
from web_api import app
async def run(operation):
 body=b'';events=[];sent=False
 scope={'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':'GET','scheme':'http',
  'path':'/api','raw_path':b'/api','root_path':'','query_string':urllib.parse.urlencode({'operation':operation,'payload':'{}'}).encode(),
  'headers':[],'client':('127.0.0.1',0),'server':('127.0.0.1',8766)}
 async def receive():
  nonlocal sent
  if not sent:sent=True;return {'type':'http.request','body':b'','more_body':False}
  await asyncio.sleep(3600)
 async def send(event):events.append(event)
 await app(scope,receive,send)
 assert next(e['status'] for e in events if e['type']=='http.response.start')==200
 return json.loads(b''.join(e.get('body',b'') for e in events))
assert asyncio.run(run('health'))['service']=='project-platform'
assert asyncio.run(run('state'))['module_errors']=={}
assert not any(n.split('.')[0] in {'torch','stockrl','rea','ai_agent','finrl'} for n in sys.modules)
print('EMPTY_HOST_OK')
"""
        environment={**os.environ,'PLATFORM_MODULES_DIR':str(empty)}
        result=subprocess.run([str(python_at(ROOT/'.venv/platform')),'-I','-X','utf8','-B','-c',code],
            cwd=ROOT,env=environment,capture_output=True,text=True,encoding='utf8',timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('EMPTY_HOST_OK',result.stdout)

    def test_large_file_download_keeps_file_streaming_and_range_support(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from module_runtime import proxy_router
        backend=self.root/'backend';backend.mkdir()
        (backend/'__init__.py').write_text('',encoding='utf8')
        (backend/'app.py').write_text("""from pathlib import Path
from fastapi import APIRouter
from .transport import FileResponse
router=APIRouter()
GROUP={'id':'files','title':'Files','menus':[]}
ROUTERS=[router]
@router.get('/api/file')
def download():return FileResponse(Path(__file__).resolve().parents[1]/'large.bin')
""",encoding='utf8')
        shutil.copy2(ROOT/'modules/rea/backend/worker.py',backend/'worker.py')
        shutil.copy2(ROOT/'modules/rea/backend/transport.py',backend/'transport.py')
        with (self.root/'large.bin').open('wb') as stream:stream.truncate(33*1024*1024)
        (self.root/'module.json').write_text(json.dumps({'id':'files','runtime':{
            'language':'python','protocol':'module-jsonl-v1','package':'download_fixture','entry':'app',
            'command':[str(python_at(ROOT/'modules/rea/.venv')),'-I','-B','{module}/backend/worker.py'],
            'state':self.root.relative_to(ROOT).as_posix()}}),encoding='utf8')
        bridge=ModuleRuntime(self.root);self.addCleanup(bridge.close)
        description=bridge.call('describe',timeout=20)
        response=bridge.call('request',{'path':'/api/file','method':'GET','body':'','headers':{}})
        self.assertEqual(Path(response['file']),self.root/'large.bin')
        self.assertEqual(response['body'],'')
        app=FastAPI();app.include_router(proxy_router(bridge,description))
        with TestClient(app) as client:
            response=client.get('/api/file',headers={'Range':'bytes=4096-4159'})
        self.assertEqual(response.status_code,206,{'body':response.text[:500],'paths':[route.path for route in app.routes]})
        self.assertEqual(response.content,b'\0'*64)

if __name__=='__main__':unittest.main()
