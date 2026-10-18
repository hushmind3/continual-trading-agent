"""Run actual exported sources with private copies of installed dependencies.

NTFS hard links reuse immutable installed package bytes; all file paths are inside
the extracted bundle. Launchers, metadata and writable files are separate copies.
No symlinks, original source imports, user data or inference requests are used.
"""
import argparse
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import Request,urlopen
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
from platform_plugins.projects import builtin_packages,store


def long_path(path):
    value=str(Path(path).resolve())
    return '\\\\?\\'+value if os.name=='nt' and not value.startswith('\\\\?\\') else value


@contextmanager
def temporary_folder(base):
    folder=Path(tempfile.mkdtemp(prefix='standalone-',dir=base))
    try:yield folder
    finally:
        if not folder.resolve().is_relative_to(base.resolve()):raise RuntimeError('검사 폴더 경계 오류')
        shutil.rmtree(long_path(folder))


def copy_environment(source,target):
    def copy(file,destination):
        path=Path(file)
        if 'site-packages' in path.parts and path.suffix not in ('.pth','.pyc') and not path.name.startswith('_module_source'):
            try:os.link(file,destination);return destination
            except OSError:pass
        return shutil.copy2(file,destination)
    def ignore(directory,names):
        return [name for name in names if name in {'__pycache__','.cache','test-results'} or (Path(directory)/name).is_symlink()]
    shutil.copytree(long_path(source),long_path(target),copy_function=copy,ignore=ignore)


def python(folder):return folder/('Scripts/python.exe' if os.name=='nt' else 'bin/python')


def api(port,operation,payload=None):
    request=Request(f'http://127.0.0.1:{port}/api',data=json.dumps({'operation':operation,'payload':payload or {}}).encode(),headers={'Content-Type':'application/json'})
    with urlopen(request,timeout=30) as response:return json.load(response)


def checked(command,cwd,env,output):
    result=subprocess.run(command,cwd=cwd,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=90)
    if result.returncode:
        output.flush()
        raise RuntimeError(Path(output.name).read_text(encoding='utf8',errors='replace')[-5000:])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('modules',nargs='*',default=['finance','rea','hermes'])
    args=parser.parse_args();results=[]
    verification=store.STATE/'verification';verification.mkdir(parents=True,exist_ok=True)
    for key in args.modules:
        started=time.monotonic()
        print(key+': 독립 소스·환경 준비',flush=True)
        with temporary_folder(verification) as temporary:
            parent=Path(temporary);original=store.STATE;store.STATE=parent/'exports'
            try:result=builtin_packages.export(key)
            finally:store.STATE=original
            archive=parent/'exports/projects'/key/'exports'/result['filename']
            outside=parent/'independent'
            with zipfile.ZipFile(archive) as bundle:bundle.extractall(outside)
            archive.unlink() # No dependency on the export file after extraction.
            copy_environment(ROOT/'.venv/platform',outside/'.venv/platform')
            copy_environment(ROOT/'modules'/key/'.venv',outside/'modules'/key/'.venv')
            source=ROOT/'node_modules';target=outside/'node_modules'
            shutil.copytree(long_path(source),long_path(target),copy_function=os.link,ignore=lambda folder,names:[name for name in names if name=='.cache' or (Path(folder)/name).is_symlink()])
            if key=='rea':
                shutil.copytree(long_path(ROOT/'modules/rea/node_modules'),long_path(outside/'modules/rea/node_modules'),copy_function=os.link)
            if key=='hermes':
                shutil.copytree(long_path(ROOT/'modules/hermes/backend/engine/browser/node_modules'),long_path(outside/'modules/hermes/backend/engine/browser/node_modules'),copy_function=os.link)
            spec=importlib.util.spec_from_file_location('isolated_runner',outside/'run.py')
            runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
            env=runner.environment();env['STANDALONE_FORBIDDEN_ROOT']=str(ROOT)
            env['PATH']=str(python(outside/'.venv/platform').parent)+os.pathsep+env.get('PATH','')
            log=parent/'execution.log'
            with log.open('w',encoding='utf8') as output:
                print(key+': 타입·화면 빌드·단독 실행 검사',flush=True)
                checked(['node',str(outside/'node_modules/typescript/bin/tsc'),'--noEmit'],outside/'frontend',env,output)
                checked(['node',str(outside/'node_modules/vite/bin/vite.js'),'build'],outside/'frontend',env,output)
                checked([sys.executable,'-I','-X','utf8','-B',str(outside/'run.py'),'check'],outside,env,output)
                with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
                process=subprocess.Popen([str(python(outside/'.venv/platform')),'-I','-X','utf8','-B','-m','uvicorn','web_api:app','--app-dir',str(outside/'backend'),'--host','127.0.0.1','--port',str(port)],cwd=outside,env=env,stdout=output,stderr=subprocess.STDOUT)
                try:
                    deadline=time.monotonic()+90
                    while True:
                        if process.poll() is not None:raise RuntimeError(log.read_text(encoding='utf8')[-3500:])
                        try:health=api(port,'health');break
                        except OSError:
                            if time.monotonic()>deadline:raise
                            time.sleep(.2)
                    modules=api(port,'platform/modules')['items']
                    assert len(modules)==1 and modules[0]['id']==key and modules[0]['available'],modules
                    assert Path(health['project']).resolve()==outside.resolve(),health
                    with urlopen(f'http://127.0.0.1:{port}/',timeout=5) as response:assert response.status==200
                    catalog=api(port,'state',{'views':'["menu_catalog"]'})
                    assert not catalog['module_errors'],catalog['module_errors']
                    if key=='hermes':
                        status=api(port,'ai_agent/Hermes/status')
                        assert not status.get('local_model',{}).get('running'),status
                    elif key=='rea':api(port,'rea/status')
                    browser_code="""import {chromium} from '@playwright/test';
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage({viewport:{width:1440,height:900}});const errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 await page.goto('http://127.0.0.1:PORT/',{waitUntil:'networkidle'});
 await page.waitForFunction(()=>document.querySelector('#root')?.textContent?.includes('TITLE'));
 if(errors.length)throw new Error(JSON.stringify(errors));
 await page.screenshot({path:'SCREENSHOT',fullPage:true});
 console.log(JSON.stringify({browser:true,errors}));
}finally{await browser.close()}
""".replace('PORT',str(port)).replace('TITLE',{'finance':'금융','rea':'REA','hermes':'헤르메스'}[key]).replace('SCREENSHOT',(verification/(key+'-standalone.png')).as_posix())
                    checked(['node','--input-type=module','-e',browser_code],outside,env,output)
                    results.append({'module':key,'host':True,'module_available':True,'ui_http':200,'browser':True,'catalog':True,'private_dependencies':True,'original_source_imports':False,'seconds':round(time.monotonic()-started,1)})
                finally:
                    try:api(port,'system/prepare-restart')
                    finally:process.terminate();process.wait(timeout=15)
            print(json.dumps(results[-1],ensure_ascii=False),flush=True)
    receipt=verification/'standalone-modules.json'
    existing=json.loads(receipt.read_text(encoding='utf8')) if receipt.is_file() else []
    combined={item['module']:item for item in existing};combined.update({item['module']:item for item in results})
    receipt.write_text(json.dumps(list(combined.values()),ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
