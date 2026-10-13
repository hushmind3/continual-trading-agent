"""Keep one original REA MCP session behind the existing project API."""
import json,os,queue,re,shutil,subprocess,threading,sys
from functools import lru_cache
from pathlib import Path
import psutil
from .. import ROOT
BASE=Path(__file__).parent
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
            self.process=subprocess.Popen([node,str(BASE/'bridge.mjs')],cwd=WORK,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,text=True,encoding='utf8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
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

def doctor(provider=None):
    node,_=node_runtime();WORK.mkdir(parents=True,exist_ok=True)
    if provider not in (None,'ghidra','hopper'):raise ValueError('지원하는 엔진을 선택하세요.')
    args=[node,str(BASE/'node_modules/rea-agents/scripts/rea.mjs'),'doctor','--format','json']
    if provider:args+=['--provider',provider]
    result=subprocess.run(args,env=runtime_environment(),cwd=WORK,capture_output=True,text=True,encoding='utf8',timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:data=json.loads(result.stdout)
    except ValueError:data={'output':result.stdout,'error':result.stderr}
    return {'exit_code':result.returncode,'result':data}

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
        providers.append({'id':name,'supported':supported,'missing':missing,
            'state':'플랫폼 미지원' if not supported else '경로 설정 필요' if missing else '필수 파일 확인 · 엔진 실행 미확인'})
    return {'values':values,'providers':providers,'platform':sys.platform}

def save_engine_settings(values):
    from ..state_io import atomic_json
    if not isinstance(values,dict) or set(values)-set(ENGINE_FIELDS):
        raise ValueError('Ghidra·JDK·Hopper의 원본 경로 설정만 저장할 수 있습니다.')
    validate_arguments(values)
    for key,value in values.items():
        if not isinstance(value,str):raise ValueError(key+': 경로는 문자열이어야 합니다.')
        if value and (not Path(value).is_absolute() or not Path(value).exists()):
            raise ValueError(key+': 존재하는 전체 경로를 입력하세요.')
        if key=='HOPPER_LAUNCHER_PATH' and value and os.name=='nt':
            raise ValueError('Hopper는 이 Windows 실행 환경에서 지원하지 않습니다.')
    if not connection.lock.acquire(blocking=False):
        raise ValueError('분석이 끝난 후 엔진 경로를 저장하세요.')
    try:
        updated=engine_environment()
        for key,value in values.items():
            if value:updated[key]=value
            else:updated.pop(key,None)
        atomic_json(updated,ENGINE_CONFIG)
        connection.close()
        tool_catalog.cache_clear()
        return engine_settings()
    finally:connection.lock.release()
