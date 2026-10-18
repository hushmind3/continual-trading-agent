"""Actual REA program/environment/data detach, independent run and restoration."""
import json,os,socket,subprocess,time
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'runtime/projects/manage/verification'
def api(op,payload=None,port=8766):
    request=Request(f'http://127.0.0.1:{port}/api',data=json.dumps({'operation':op,'payload':payload or {}}).encode(),headers={'Content-Type':'application/json'})
    with urlopen(request,timeout=15) as response:return json.load(response)
def until(callback,seconds=240):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        try:
            value=callback()
            if value:return value
        except OSError:pass
        time.sleep(1)
    raise RuntimeError('API/menu waiting timeout')
def record():return api('projects/detail',{'id':'rea'})
def stage(wanted):
    item=record()
    if item.get('error'):raise RuntimeError(item['error'])
    return item if item['stage']==wanted else None
process=None;outside=None;requested=False
before=(ROOT/'modules/rea/backend/worker.py').read_bytes()
try:
    assert not api('system/blockers')['items']
    requested=True;api('projects/detach',{'id':'rea'})
    detached=until(lambda:stage('removed'));outside=Path(detached['standalone_path'])
    assert not (ROOT/'modules/rea').exists()
    assert (outside/'modules/rea/.venv/Scripts/python.exe').is_file()
    until(lambda:'rea' not in api('projects/installed')['active_module_ids'])
    print('REA actual source/environment/data detached',flush=True)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    environment=os.environ.copy()
    for key in ('PLATFORM_ROOT','PLATFORM_MODULES_DIR','PYTHONPATH','HERMES_HOME'):environment.pop(key,None)
    with (BASE/'builtin-detachment.log').open('w',encoding='utf8') as output:
        process=subprocess.Popen([str(outside/'.venv/platform/Scripts/python.exe'),'-I','-X','utf8','-B','-m','uvicorn','web_api:app','--app-dir',str(outside/'backend'),'--host','127.0.0.1','--port',str(port)],cwd=outside,env=environment,stdout=output,stderr=subprocess.STDOUT)
        health=until(lambda:api('health',port=port),45)
        assert Path(health['project']).resolve()==outside.resolve()
        entries=api('platform/modules',port=port)['items']
        assert len(entries)==1 and entries[0]['id']=='rea' and entries[0]['available'],entries
        api('rea/status',port=port)
        code="""const {chromium}=require('@playwright/test');(async()=>{const browser=await chromium.launch({headless:true});try{const page=await browser.newPage({viewport:{width:1440,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('http://127.0.0.1:PORT/#rea/program_analysis');await page.getByRole('main').getByText('프로그램 분석',{exact:true}).first().waitFor();await page.screenshot({path:'SCREENSHOT',fullPage:true});if(errors.length)throw new Error(JSON.stringify(errors));}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});""".replace('PORT',str(port)).replace('SCREENSHOT',(BASE/'builtin-detached-rea.png').as_posix())
        subprocess.run(['node','-e',code],cwd=ROOT,check=True,timeout=45,stdout=output,stderr=subprocess.STDOUT)
        print('REA independent API/browser/status verified',flush=True)
        api('system/prepare-restart',port=port);process.terminate();process.wait(timeout=20);process=None
    api('projects/reconnect',{'id':'rea'});requested=False
    until(lambda:any(item['id']=='rea' and item['stage']=='ready' for item in api('projects/installed')['items']))
    assert (ROOT/'modules/rea/backend/worker.py').read_bytes()==before
    assert (ROOT/'modules/rea/.venv/Scripts/python.exe').is_file()
    report={'actual_source_moved':True,'private_environment_moved':True,'owned_data_moved':True,'independent_api':True,'independent_browser':True,'rea_status':True,'reconnected':True,'source_preserved':True,'model_inference':False}
    (BASE/'builtin-detachment.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report),flush=True)
finally:
    if process:
        try:api('system/prepare-restart',port=port)
        except Exception:pass
        process.terminate();process.wait(timeout=20)
    if requested:
        value=until(lambda:record() if record()['stage']!='detaching' else None)
        if value['stage']=='removed':api('projects/reconnect',{'id':'rea'})
