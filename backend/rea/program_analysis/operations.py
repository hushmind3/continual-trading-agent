"""Keep one original REA MCP session behind the existing project API."""
import json,os,queue,re,shutil,subprocess,threading,sys
from functools import lru_cache
from pathlib import Path
import psutil
from stockrl import ROOT
BASE=Path(__file__).parent.parent
WORK=ROOT/'runtime/rea'
SOURCE='https://github.com/morluto/rea'

@lru_cache(maxsize=1)
def node_runtime():
    choices=[os.environ.get('STOCKRL_REA_NODE'),shutil.which('node')]
    choices += [str(p/'node.exe') for p in sorted((Path.home()/'AppData/Local/Programs').glob('node-v*-win-x64'),reverse=True)]
    for candidate in dict.fromkeys(p for p in choices if p):
        try:
            result=subprocess.run([candidate,'--version'],capture_output=True,text=True,timeout=5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            match=re.fullmatch(r'v(\d+)\.(\d+)\.(\d+)\s*',result.stdout)
            if match:
                major,minor,_=map(int,match.groups())
                if major>=26 or major==24 and minor>=11 or major==22 and minor>=19:return candidate,result.stdout.strip()
        except (OSError,subprocess.TimeoutExpired):pass
    raise RuntimeError('REA에는 Node 22.19+, 24.11+ 또는 26+가 필요합니다. STOCKRL_REA_NODE로 실행 파일을 지정하세요.')

def validate_arguments(value):
    if isinstance(value,dict):
        for item in value.values():validate_arguments(item)
    elif isinstance(value,list):
        for item in value:validate_arguments(item)
    elif isinstance(value,str) and not value.startswith(('https://','http://')):
        if '휴지통' in value.replace('\\','/').split('/'):raise ValueError('휴지통은 REA 입력·출력으로 사용하지 않습니다.')
        try:
            path=Path(value).expanduser().resolve()
            if path==ROOT/'휴지통' or ROOT/'휴지통' in path.parents:raise ValueError('휴지통은 REA 입력·출력으로 사용하지 않습니다.')
        except OSError:pass

class REAConnection:
    def __init__(self):self.lock=threading.RLock();self.process=None;self.responses=None
    def start(self):
        if self.process and self.process.poll() is None:return
        node,_=node_runtime();WORK.mkdir(parents=True,exist_ok=True);responses=queue.Queue();self.responses=responses
        env=runtime_environment()
        with (WORK/'mcp.stderr.log').open('ab') as errors:
            self.process=subprocess.Popen([node,str(BASE/'program_analysis/bridge.mjs')],cwd=WORK,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,text=True,encoding='utf8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if os.name=='nt':
            try:
                owner=psutil.Process(self.process.pid)
                for process in [owner,*owner.children(recursive=True)]:
                    process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                    process.cpu_affinity(process.cpu_affinity()[:2])
            except psutil.Error as exc:
                self.close();raise RuntimeError('REA CPU 사용 제한 적용 실패: '+str(exc)) from exc
        stream=self.process.stdout
        def receive():
            try:
                for line in stream:
                    try:responses.put(json.loads(line))
                    except ValueError:responses.put({'error':'REA 연결이 JSON 응답을 반환하지 않았습니다.'})
            finally:responses.put({'error':'REA 연결이 종료됐습니다. 환경 진단을 확인하세요.'})
        threading.Thread(target=receive,name='rea-mcp-response',daemon=True).start()
    def request(self,payload,timeout=600):
        with self.lock:
            self.start();process=self.process
            try:
                process.stdin.write(json.dumps(payload,ensure_ascii=False)+'\n');process.stdin.flush()
                result=self.responses.get(timeout=timeout)
            except queue.Empty:
                self.close();raise RuntimeError('REA 응답 시간이 초과되어 분석 세션을 닫았습니다.') from None
            except (OSError,ValueError) as exc:raise RuntimeError('REA 연결 오류: '+str(exc)) from exc
            if result.get('error'):raise RuntimeError(result['error'])
            return result['result']
    def close(self):
        process=self.process
        if not process:return
        if process.poll() is None:
            try:
                parent=psutil.Process(process.pid);children=parent.children(recursive=True)
                for child in reversed(children):
                    try:child.terminate()
                    except psutil.Error:pass
                parent.terminate();_,alive=psutil.wait_procs([*children,parent],timeout=5)
                for child in alive:
                    try:child.kill()
                    except psutil.Error:pass
            except psutil.Error:pass
        for stream in (process.stdin,process.stdout):
            try:stream.close()
            except (OSError,ValueError):pass
        self.process=None

connection=REAConnection()

@lru_cache(maxsize=1)
def tool_catalog(version):return connection.request({'operation':'tools'},60)['tools']

def status():
    package=BASE/'node_modules/rea-agents/package.json'
    if not package.is_file():return {'installed':False,'source':SOURCE,'tools':[],'reason':'REA가 설치되지 않았습니다. 설치.cmd 또는 REA 폴더의 npm ci를 실행하세요.'}
    metadata=json.loads(package.read_text(encoding='utf8'))
    try:
        node,version=node_runtime();tools=tool_catalog(metadata['version']);engines=engine_settings()
    except (OSError,RuntimeError,ValueError) as exc:return {'installed':False,'version':metadata['version'],'source':SOURCE,'tools':[],'reason':str(exc)}
    return {'installed':True,'version':metadata['version'],'source':SOURCE,'node_version':version,'tools':tools,'tool_count':len(tools),'session_connected':bool(connection.process and connection.process.poll() is None),'engines':engines}

def call_tool(name,arguments):
    validate_arguments(arguments);available=status()
    if not available['installed']:raise RuntimeError(available['reason'])
    if name not in {tool['name'] for tool in available['tools']}:raise ValueError('원본 REA에 등록된 도구를 선택하세요.')
    return connection.request({'operation':'call','tool':name,'arguments':arguments})


def install():
    node,_=node_runtime();npm=shutil.which('npm')
    if not npm:raise RuntimeError('npm이 설치되지 않았습니다.')
    npm_path=Path(npm).resolve().parent/'node_modules/npm/bin/npm-cli.js'
    if not npm_path.is_file():npm_path=Path(node).parent/'node_modules/npm/bin/npm-cli.js'
    if not npm_path.is_file():raise RuntimeError('npm-cli.js를 찾을 수 없습니다.')
    env=os.environ.copy();env['PATH']=str(Path(node).parent)+os.pathsep+env.get('PATH','')
    if os.name=='nt':env['ComSpec']=str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/cmd.exe')
    subprocess.run([node,str(npm_path),'ci','--no-audit','--no-fund'],cwd=BASE,env=env,check=True)

# Project-scoped engine settings; never edit Codex/client/global environment.
ENGINE_CONFIG=ROOT/'configs/local/rea.json'
ENGINE_FIELDS=('GHIDRA_INSTALL_DIR','JAVA_HOME','HOPPER_LAUNCHER_PATH')

def engine_environment():
    if not ENGINE_CONFIG.is_file():return {}
    value=json.loads(ENGINE_CONFIG.read_text(encoding='utf8'))
    if not isinstance(value,dict) or set(value)-set(ENGINE_FIELDS):
        raise ValueError('REA 엔진 설정 파일의 입력 이름을 확인하세요.')
    if any(not isinstance(item,str) for item in value.values()):
        raise ValueError('REA 엔진 경로는 문자열이어야 합니다.')
    validate_arguments(value)
    return {key:item for key,item in value.items() if item}

def runtime_environment():
    value=os.environ.copy();value.update(engine_environment())
    value.update(NO_COLOR='1',PYTHONUTF8='1')
    return value

def engine_settings():
    configured=engine_environment()
    values={key:configured.get(key,os.environ.get(key,'')) for key in ENGINE_FIELDS}
    suffix='.exe' if os.name=='nt' else ''
    checks={
        'ghidra':[('GHIDRA_INSTALL_DIR','support/analyzeHeadless.bat' if os.name=='nt' else 'support/analyzeHeadless'),
                  ('JAVA_HOME','bin/java'+suffix),('JAVA_HOME','bin/javac'+suffix)],
        'hopper':[('HOPPER_LAUNCHER_PATH',None)],
    }
    providers=[]
    for name,required in checks.items():
        missing=[]
        for key,relative in required:
            path=values[key]
            if not path or not (Path(path)/relative if relative else Path(path)).is_file():
                missing.append(key+('/'+relative if relative else ''))
        supported=name!='hopper' or os.name!='nt'
        from stockrl.state_io import read_json
        readiness=read_json(WORK/(name+'-readiness.json'))
        verified=not missing and readiness.get('settings')==values and readiness.get('exit_code')==0
        providers.append({'id':name,'supported':supported,'missing':missing,
            'state':'플랫폼 미지원' if not supported else '경로 설정 필요' if missing else '원본 엔진 준비 확인 통과' if verified else '필수 파일 확인 · 엔진 실행 미확인'})
    return {'values':values,'providers':providers,'platform':sys.platform}



def native_recover(path):
    """Compose official Ghidra tools for the file explicitly selected by the user."""
    import hashlib
    if not isinstance(path,str) or not path:raise ValueError('복원할 파일을 선택하세요.')
    validate_arguments(path)
    target=Path(path).expanduser().resolve()
    if not target.is_file():
        raise ValueError('복원할 실제 실행파일·라이브러리를 선택하세요.')
    def observe(tool,arguments):
        response=call_tool(tool,arguments)
        if response.get('isError'):
            messages=[block.get('text','') for block in response.get('content',[]) if block.get('type')=='text']
            raise RuntimeError('\n'.join(messages) or '원본 디컴파일 도구 실행 실패')
        record=response.get('structuredContent')
        if not isinstance(record,dict):
            record=next((json.loads(block['text']) for block in response.get('content',[]) if block.get('type')=='text'),None)
        if tool=='open_binary':
            if not isinstance(record,dict) or not isinstance(record.get('result'),dict):
                raise RuntimeError('원본 파일 열기 결과를 확인할 수 없습니다.')
            return record
        if not isinstance(record,dict) or 'normalized_result' not in record:
            raise RuntimeError('원본 도구의 분석 결과 형식을 확인할 수 없습니다.')
        return record
    with connection.lock:
        opened=None
        try:
            digest=hashlib.sha256()
            with target.open('rb') as stream:
                while chunk:=stream.read(1024*1024):digest.update(chunk)
            opened=observe('open_binary',{'path':str(target),'provider_id':'ghidra'})
            if opened['result'].get('sha256')!=digest.hexdigest():
                raise RuntimeError('선택한 파일이 분석 중 변경됐습니다. 파일을 다시 선택하세요.')
            inventory=observe('list_procedures',{})
            procedures=inventory['normalized_result']
            if not isinstance(procedures,list):
                raise RuntimeError('원본 함수 목록이 배열 형식이 아닙니다.')
            addresses=[item['address'] for item in procedures]
            batch=observe('batch_decompile',{'addresses':addresses})
            value=batch['normalized_result']
            if not isinstance(value,dict) or not isinstance(value.get('items'),list):
                raise RuntimeError('원본 일괄 디컴파일 결과를 확인할 수 없습니다.')
            lines=['/* Ghidra decompiled C-like code. Not the original source project.',
                   ' * File: '+target.name,' * SHA256: '+digest.hexdigest(),' */','']
            for item in value['items']:
                name=(item.get('procedure') or {}).get('name') or item['address']
                lines.append('/* '+str(name).replace('*/','* /')+' @ '+item['address']+' */')
                if item.get('status')=='ok' and isinstance(item.get('pseudocode'),str):
                    lines.append(item['pseudocode'])
                else:
                    lines.append('/* Decompilation unavailable: '+json.dumps(item.get('error'),ensure_ascii=False).replace('*/','* /')+' */')
                lines.append('')
            source='\n'.join(lines)
            from stockrl.state_io import atomic_json
            import uuid
            output=WORK/'recovered'/uuid.uuid4().hex
            output.mkdir(parents=True)
            (output/(target.stem+'.decompiled.c')).write_text(source,encoding='utf8')
            atomic_json(batch,output/'evidence.json')
            return {'name':target.name,'path':str(target),'sha256':digest.hexdigest(),
                'total':value['total'],'succeeded':value['succeeded'],'failed':value['failed'],
                'items':value['items'],'source':source,
                'output':str(output.relative_to(ROOT)),'limitations':batch.get('limitations',[])}

        finally:
            if opened and connection.process and connection.process.poll() is None:
                response=call_tool('close_binary',{})
                if response.get('isError'):
                    connection.close();raise RuntimeError('원본 분석 종료 실패로 소유 REA 세션을 정리했습니다.')
