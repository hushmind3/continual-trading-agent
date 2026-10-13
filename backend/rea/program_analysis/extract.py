"""REA analysis and physical source projects. No coding agent or program runner."""
from __future__ import annotations
import hashlib,json,mimetypes,os,re,shutil,subprocess,sys,threading,time,uuid,zipfile
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen
import psutil
from stockrl import ROOT
from stockrl.state_io import atomic_json
from rea.program_analysis.operations import BASE
from rea.program_analysis.operations import WORK
from rea.program_analysis.operations import call_tool
from rea.program_analysis.operations import connection
from rea.program_analysis.operations import native_recover
from rea.program_analysis.operations import node_runtime
from rea.program_analysis.operations import runtime_environment
from rea.program_analysis.operations import validate_arguments

from rea.project_explorer.projects import OUTPUT
from rea.project_explorer.projects import _inside
_gate=threading.Lock()
_cancel=threading.Event()
_processes=[]

def _check():
    if _cancel.is_set():raise RuntimeError('사용자가 분석을 중지했습니다.')

def _spawn(args,**kwargs):
    _check()
    process=subprocess.Popen(args,env=runtime_environment(),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),**kwargs)
    _processes.append(process)
    if os.name=='nt':
        owner=psutil.Process(process.pid);owner.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        owner.cpu_affinity(owner.cpu_affinity()[:2])
    return process

def stop():
    _cancel.set();connection.close()
    for process in list(_processes):
        if process.poll() is not None:continue
        try:
            owner=psutil.Process(process.pid);children=owner.children(recursive=True)
            for child in reversed(children):child.terminate()
            owner.terminate();_,alive=psutil.wait_procs([*children,owner],timeout=3)
            for child in alive:child.kill()
        except psutil.Error:pass

def _observe(name,arguments):
    _check()
    result=call_tool(name,arguments)
    if result.get('isError'):
        raise RuntimeError('\n'.join(block.get('text','') for block in result.get('content',[]) if block.get('type')=='text'))
    record=result.get('structuredContent')
    if record is None:record=json.loads(next(block['text'] for block in result['content'] if block['type']=='text'))
    return record

def pick(kind):
    if kind not in ('file','folder'):raise ValueError('파일 또는 폴더를 선택하세요.')
    script="""import json,sys,tkinter as tk
from tkinter import filedialog
root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
value=filedialog.askdirectory(title='분석할 폴더 선택',parent=root) if sys.argv[1]=='folder' else filedialog.askopenfilename(title='분석할 파일 선택',parent=root)
root.destroy();print(json.dumps({'path':value},ensure_ascii=False))
"""
    result=subprocess.run([sys.executable,'-c',script,kind],capture_output=True,text=True,encoding='utf8',env=runtime_environment(),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise RuntimeError('파일 선택창을 열지 못했습니다: '+result.stderr[-1000:])
    return json.loads(result.stdout)







def _javascript(target,folder):
    node,_=node_runtime();analysis=folder/'analysis'
    with (analysis/'evidence.json').open('wb') as output,(analysis/'progress.log').open('wb') as log:
        process=_spawn([node,str(BASE/'node_modules/rea-agents/scripts/rea.mjs'),'analyze-javascript-application',str(target),'--json'],cwd=BASE,stdout=output,stderr=log)
        code=process.wait()
    _check()
    if code:raise RuntimeError('REA JavaScript 분석 실패: '+(analysis/'progress.log').read_text(encoding='utf8',errors='replace')[-2000:])
    evidence=json.loads((analysis/'evidence.json').read_text(encoding='utf8'))
    data=evidence['normalized_result']
    for key in ('graph','semantic_graph','summary','statistics','limitations'):
        if key in data:atomic_json(data[key],analysis/(key+'.json'))
    modules={}
    inferred=[]
    for node in data.get('graph',{}).get('nodes',[]):
        for observation in node.get('observations',[]):
            module=observation.get('properties',{}).get('module_path')
            if observation.get('evidence',{}).get('state')=='inferred':
                inferred.append({'node_id':node['node_id'],'module':module,'observation':observation})
            elif module:modules.setdefault(module,[]).append({'node_id':node['node_id'],'observation':observation})
    module_dir=analysis/'modules';module_dir.mkdir()
    for module,observations in modules.items():
        name=re.sub(r'[^a-zA-Z0-9_.-]','_',Path(module).name)+'-'+hashlib.sha256(module.encode()).hexdigest()[:8]+'.json'
        atomic_json({'module':module,'observations':observations},module_dir/name)
    functions=analysis/'functions';functions.mkdir()
    for node in data.get('semantic_graph',{}).get('nodes',[]):
        if node.get('kind')=='function':
            name=re.sub(r'[^a-zA-Z0-9_.-]','_',node.get('label') or 'function')[:60]+'-'+node['node_id'][-12:]+'.json'
            atomic_json(node,functions/name)
    atomic_json(inferred,folder/'inferred/relationships.json')
    return data.get('limitations',[])

def _copy_directory(target,destination):
    unavailable=[]
    destination.mkdir(parents=True)
    for base,dirs,files in os.walk(target,followlinks=False):
        _check()
        dirs[:]=[name for name in dirs if name!='.git' and not (Path(base)/name).is_symlink() and (Path(base)/name).resolve() not in {OUTPUT.resolve(),WORK.resolve(),destination.parent.parent.resolve()}]
        for name in files:
            _check();source=Path(base)/name;relative=source.relative_to(target)
            if source.is_symlink():unavailable.append({'path':str(relative),'reason':'symbolic link'});continue
            output=destination/relative;output.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,output)
    return unavailable

def _asar(target,destination,analysis):
    node,_=node_runtime()
    process=_spawn([node,str(BASE/'program_analysis/artifacts.mjs'),str(target),str(destination)],cwd=BASE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    output,error=process.communicate();_check()
    if process.returncode:raise RuntimeError(error.decode('utf8',errors='replace')[-1500:])
    result=json.loads(output);atomic_json(result,analysis/'extraction.json')
    return result['unavailable']

def _web(url,folder):
    parsed=urlparse(url)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('분석할 http/https 웹사이트 주소를 입력하세요.')
    chrome=next((path for path in [Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'Google/Chrome/Application/chrome.exe',
        Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Microsoft/Edge/Application/msedge.exe'] if path.is_file()),None)
    if not chrome:raise RuntimeError('설치된 Chrome 또는 Edge가 필요합니다.')
    profile=WORK/'browser'/uuid.uuid4().hex;profile.mkdir(parents=True)
    browser=_spawn([str(chrome),'--headless=new','--remote-debugging-port=0','--remote-debugging-address=127.0.0.1',
        '--user-data-dir='+str(profile),'--no-first-run','--no-default-browser-check',url],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        deadline=time.monotonic()+30
        port=None
        while port is None:
            _check()
            if time.monotonic()>deadline:raise RuntimeError('분석 브라우저 연결 시간이 초과됐습니다.')
            try:
                lines=(profile/'DevToolsActivePort').read_text().splitlines()
                if lines and lines[0].isdigit():port=lines[0]
            except OSError:pass
            if port is None:time.sleep(.1)
        endpoint='http://127.0.0.1:'+port
        deadline=time.monotonic()+30;target=None
        while time.monotonic()<deadline:
            _check()
            with urlopen(endpoint+'/json/list',timeout=5) as response:pages=json.load(response)
            target=next((page for page in pages if page['type']=='page' and page['url'].startswith(('http://','https://'))),None)
            if target:break
            time.sleep(.1)
        if not target:raise RuntimeError('분석할 웹페이지가 없습니다.')
        origin=urlparse(target['url']);origin=origin.scheme+'://'+origin.netloc
        args={'cdp_endpoint':endpoint,'target_id':target['id'],'allowed_origins':[origin],'include_script_sources':True}
        capture=_observe('inspect_web_page',args);atomic_json(capture,folder/'analysis/web-capture.json')
        export=_observe('export_web_scripts',{'capture_path':str(folder/'analysis/web-capture.json'),'output_directory':str(folder/'original/scripts')})
        atomic_json(export,folder/'analysis/script-export.json')
        bundle=_observe('analyze_web_bundle',args);atomic_json(bundle,folder/'analysis/web-structure.json')
        data=bundle['normalized_result']
        atomic_json(data.get('inferences',[]),folder/'inferred/web-inferences.json')
        with urlopen(url,timeout=30) as response:
            html=response.read();(folder/'original/index.html').write_bytes(html)
            atomic_json({'requested_url':url,'received_url':response.url,'sha256':hashlib.sha256(html).hexdigest()},folder/'analysis/html-origin.json')
        return data.get('limitations',[])+['웹 서버 내부 소스는 수집하지 않았습니다. 로그인·사용자 동작을 자동화하지 않았습니다.']
    finally:
        try:
            owner=psutil.Process(browser.pid);children=owner.children(recursive=True)
            for child in reversed(children):child.terminate()
            owner.terminate();_,alive=psutil.wait_procs([*children,owner],timeout=3)
            for child in alive:child.kill()
        except psutil.Error:pass

def analyze(kind,target):
    if kind not in ('file','folder','web') or not isinstance(target,str) or not target.strip():
        raise ValueError('분석할 파일·폴더·웹사이트를 선택하세요.')
    if not _gate.acquire(blocking=False):raise RuntimeError('진행 중인 REA 분석이 있습니다.')
    _cancel.clear();_processes.clear();identifier=uuid.uuid4().hex
    display=urlparse(target).hostname if kind=='web' else Path(target).name
    display=re.sub(r'[^A-Za-z0-9._-]+','_',display or '').strip(' ._')[:90] or {'file':'file_project','folder':'folder_project','web':'website_project'}[kind]
    if display.upper().split('.')[0] in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:display='target_'+display
    folder=OUTPUT/(display+'__'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir(parents=True)
    for name in ('original','inferred','analysis'):(folder/name).mkdir()
    metadata={'id':identifier,'name':urlparse(target).hostname if kind=='web' else Path(target).name,
              'input':target,'kind':kind,'state':'analyzing','folder':str(folder),
              'created_at':datetime.now(timezone.utc).isoformat()}
    atomic_json(metadata,folder/'project.json')
    try:
        unavailable=[];limitations=[]
        if kind=='web':
            metadata['artifact']='웹사이트 프론트엔드';limitations=_web(target,folder)
        else:
            validate_arguments(target);source=Path(target).expanduser().resolve()
            if not source.exists():raise ValueError('선택한 경로가 없습니다.')
            asar=source if source.suffix.lower()=='.asar' else next((candidate for candidate in
                [(source if source.is_dir() else source.parent)/'resources/app.asar',
                 (source if source.is_dir() else source.parent)/'app.asar'] if candidate.is_file()),None)
            if asar:
                metadata['artifact']='Electron / ASAR';limitations=_javascript(asar,folder)
                unavailable=_asar(asar,folder/'original',folder/'analysis')
            elif source.is_dir():
                metadata['artifact']='JavaScript / 소스 폴더'
                unavailable=_copy_directory(source,folder/'original/source')
                limitations=_javascript(folder/'original/source',folder)
            elif source.suffix.lower() in ('.js','.jsx','.mjs','.cjs','.ts','.tsx','.html','.css','.json','.py','.c','.cpp','.h','.rs','.go','.java','.cs'):
                metadata['artifact']='소스 파일';shutil.copyfile(source,folder/'original'/source.name)
                if source.suffix.lower() in ('.js','.jsx','.mjs','.cjs','.ts','.tsx','.html'):
                    limitations=_javascript(folder/'original',folder)
                else:limitations=['관측한 소스 원문을 보관했습니다. 이 파일의 언어별 의미 그래프는 생성하지 않았습니다.']
            elif source.suffix.lower() in ('.apk','.ipa','.zip'):
                metadata['artifact']='패키지 / 리소스'
                with zipfile.ZipFile(source) as archive:
                    for item in archive.infolist():
                        _check();output=_inside(folder/'original',item.filename.replace('\\','/'))
                        if (item.external_attr>>16)&0o170000==0o120000:
                            unavailable.append({'path':item.filename,'reason':'archive symbolic link'});continue
                        if item.is_dir():output.mkdir(parents=True,exist_ok=True);continue
                        output.parent.mkdir(parents=True,exist_ok=True)
                        with archive.open(item) as incoming,output.open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing)
                if source.suffix.lower()=='.apk':atomic_json(_observe('inspect_android_package',{'path':str(source)}),folder/'analysis/android.json')
                limitations=['패키지 파일·리소스를 추출했습니다. DEX/ARM/Mach-O 원본 소스나 서버 구현을 복원한 것이 아닙니다.']
            else:
                metadata['artifact']='네이티브 PE';shutil.copyfile(source,folder/'original'/source.name)
                recovered=native_recover(str(source))
                (folder/'inferred/decompiled.c').write_text(recovered['source'],encoding='utf8')
                functions=folder/'inferred/functions';functions.mkdir()
                for item in recovered['items']:
                    if item['status']=='ok':(functions/(re.sub(r'[^a-zA-Z0-9_-]','_',item['address'])+'.c')).write_text(item['pseudocode'],encoding='utf8')
                atomic_json(recovered['items'],folder/'analysis/functions.json')
                atomic_json({'sha256':recovered['sha256'],'total':recovered['total'],'decompiled':recovered['succeeded'],'unavailable':recovered['failed']},folder/'analysis/structure.json')
                limitations=recovered['limitations']+['네이티브 C 의사코드는 추론된 결과입니다. 컴파일 전 원본 소스가 아닙니다.']
        _check();atomic_json(unavailable,folder/'analysis/unavailable.json')
        original=[path for path in (folder/'original').rglob('*') if path.is_file()]
        manifest=[{'path':path.relative_to(folder).as_posix(),'bytes':path.stat().st_size} for path in original]
        atomic_json(manifest,folder/'analysis/module-files.json')
        metadata.update(state='saved',original_files=len(original),
            inferred_files=sum(1 for path in (folder/'inferred').rglob('*') if path.is_file()),limitations=limitations,unavailable=len(unavailable))
        readme='# '+str(metadata['name'])+' — REA 분석 자료\n\noriginal/: 관측·추출한 원문/파일. 네이티브 바이너리 자체는 원본 소스코드가 아닙니다.\ninferred/: Ghidra 의사코드 및 REA 추론. 원문과 구분합니다.\nanalysis/: 구조·함수·모듈 정보, 출처와 한계.\n\n코딩 에이전트 호출·프로그램 재구현·추출 프로그램 실행은 수행하지 않았습니다.\n\n## 분석 범위\n'+('\n'.join('- '+str(item) for item in limitations) or '- 관측한 입력 범위의 정적 분석 자료입니다.')+'\n'
        (folder/'README.md').write_text(readme,encoding='utf8')
        atomic_json(metadata,folder/'project.json');return metadata
    except Exception as error:
        metadata.update(state='stopped' if _cancel.is_set() else 'failed',error=str(error))
        atomic_json(metadata,folder/'project.json');raise
    finally:_processes.clear();_gate.release()
