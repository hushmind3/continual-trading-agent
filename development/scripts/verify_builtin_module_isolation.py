"""Temporarily detach the three real modules, verify the host, and always restore."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
import urllib.request
import tempfile

ROOT=Path(__file__).resolve().parents[2]
VERIFY=ROOT/'runtime/platform/module-verification'
NAMES=('finance','rea','hermes')

def api(operation):
    request=urllib.request.Request('http://127.0.0.1:8766/api',data=json.dumps({'operation':operation,'payload':{}}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)

def apply(environment):
    subprocess.run([str(ROOT/'.venv/platform/Scripts/python.exe'),'-I','-X','utf8','-B',
        str(ROOT/'development/scripts/start_server.py'),'--apply-only','--skip-checks'],
        cwd=ROOT,env=environment,check=True,timeout=180)

def main():
    VERIFY.mkdir(parents=True,exist_ok=True)
    parked=VERIFY/'parked-modules'
    if parked.exists():raise RuntimeError('이전 분리 검사 보관 폴더가 남아 있습니다. 덮어쓰지 않습니다.')
    if reasons:=api('system/blockers')['items']:raise RuntimeError('실행 중 작업: '+repr(reasons))
    # Finish applying and validating source changes before closing the active workers.
    apply(os.environ.copy())
    api('system/prepare-restart')
    parked.mkdir();moved=[];report={'started_at':time.time(),'data_moved':False,'central_source_modified_by_test':False}
    try:
        for name in NAMES:
            source=(ROOT/'modules'/name).resolve();target=(parked/name).resolve()
            if source!=ROOT/'modules'/name or not target.is_relative_to(VERIFY.resolve()) or target.exists():
                raise RuntimeError('분리 경계/충돌 확인 실패: '+name)
            source.rename(target);moved.append(name)
        environment={**os.environ,'PLATFORM_READ_ONLY':'1'}
        apply(environment)
        modules=api('platform/modules')['items']
        assert [item['id'] for item in modules]==['projects'],modules
        assert all(item.get('available') for item in modules),modules
        assert api('state')['module_errors']=={}
        assert Path(api('health')['python_prefix']).resolve()==(ROOT/'.venv/platform').resolve()
        probe="""import assert from 'node:assert/strict';import {chromium} from '@playwright/test';
const browser=await chromium.launch({headless:true});try{const page=await browser.newPage();const errors=[];
page.on('pageerror',e=>errors.push(e.message));await page.goto('http://127.0.0.1:8766/#projects/manage/installed');
await page.getByText('서버 연결',{exact:true}).waitFor({timeout:30000});
await page.getByRole('navigation',{name:'GitHub',exact:true}).waitFor();
assert.equal(await page.getByRole('navigation',{name:'금융',exact:true}).count(),0);
assert.equal(await page.getByRole('navigation',{name:'REA 역공학',exact:true}).count(),0);
assert.equal(await page.getByRole('navigation',{name:'AI 에이전트',exact:true}).count(),0);
assert.deepEqual(errors,[]);console.log('DETACHED_HOST_UI_OK');}finally{await browser.close();}
"""
        subprocess.run(['node','--input-type=module','-e',probe],cwd=ROOT,check=True,timeout=60)
        report.update(detached_host=True,detached_ui=True,loaded_modules=[item['id'] for item in modules])
        # Run the real relocated packages while their original module paths are absent.
        sys.path.insert(0,str(ROOT/'backend'))
        from module_runtime import ModuleRuntime
        relocated={}
        for name in ('finance','rea'):
            bridge=ModuleRuntime(parked/name)
            try:
                description=bridge.call('describe',timeout=60)
                assert Path(description['module'])==(parked/name).resolve(),description
                assert Path(description['prefix'])==(parked/name/'.venv').resolve(),description
                assert Path(description['source']).is_relative_to((parked/name).resolve()),description
                for value in description['dependencies'].values():assert Path(value).is_relative_to((parked/name/'.venv').resolve()),description
                relocated[name]={'routes':len(description['routes']),'private_packages':True}
            finally:bridge.close()
        environment={**os.environ,'PLATFORM_ROOT':str(ROOT)}
        rea=subprocess.run([str(parked/'rea/.venv/Scripts/python.exe'),'-I','-X','utf8','-B','-c',
            "from rea.program_analysis.operations import status,connection;v=status();connection.close();assert v['installed'],v;print(v['tool_count'])"],
            cwd=ROOT,env=environment,capture_output=True,text=True,encoding='utf8',check=True,timeout=60)
        relocated['rea']['mcp_tools']=int(rea.stdout.strip())
        with tempfile.TemporaryDirectory(dir=VERIFY) as home:
            environment.update(HERMES_HOME=home,HERMES_RUNTIME_DIR=str(Path(home)/'runtime'))
            message=json.dumps({'id':'status','operation':'status','payload':{}})+'\n'+json.dumps({'id':'stop','operation':'shutdown','payload':{}})+'\n'
            result=subprocess.run([str(parked/'hermes/.venv/Scripts/python.exe'),'-I','-X','utf8','-B',str(parked/'hermes/backend/engine/worker.py')],
                cwd=ROOT,env=environment,input=message,capture_output=True,text=True,encoding='utf8',timeout=60,check=True)
            answers=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
            status=next(item for item in answers if item.get('id')=='status')
            assert not status.get('error'),status
            relocated['hermes']={'status':True,'temporary_home':True,'model_loaded':False}
        report['relocated_execution']=relocated
    finally:
        for name in reversed(moved):
            source=(parked/name).resolve();target=ROOT/'modules'/name
            if target.exists():raise RuntimeError('복원 대상 충돌; 원본은 보관 위치에 유지합니다: '+str(source))
            source.rename(target)
        if parked.exists():parked.rmdir()
        environment=os.environ.copy();environment.pop('PLATFORM_READ_ONLY',None)
        apply(environment)
        report['restored_modules']=[item['id'] for item in api('platform/modules')['items'] if item.get('available')]
        report['restored']=all(name in report['restored_modules'] for name in NAMES)
        report['finished_at']=time.time()
        (VERIFY/'builtin-isolation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    assert report['restored'],report
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
