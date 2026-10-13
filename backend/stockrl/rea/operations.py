"""Keep one original REA MCP session behind the existing project API."""
import json,os,queue,re,shutil,subprocess,threading
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
        env=os.environ.copy();env.update(NO_COLOR='1',PYTHONUTF8='1')
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
        node,version=node_runtime();tools=tool_catalog(metadata['version'])
    except (OSError,RuntimeError,ValueError) as exc:return {'installed':False,'version':metadata['version'],'source':SOURCE,'tools':[],'reason':str(exc)}
    return {'installed':True,'version':metadata['version'],'source':SOURCE,'node_version':version,'tools':tools,'tool_count':len(tools),'session_connected':bool(connection.process and connection.process.poll() is None)}

def call_tool(name,arguments):
    validate_arguments(arguments);available=status()
    if not available['installed']:raise RuntimeError(available['reason'])
    if name not in {tool['name'] for tool in available['tools']}:raise ValueError('원본 REA에 등록된 도구를 선택하세요.')
    return connection.request({'operation':'call','tool':name,'arguments':arguments})

def doctor():
    node,_=node_runtime();WORK.mkdir(parents=True,exist_ok=True)
    result=subprocess.run([node,str(BASE/'node_modules/rea-agents/scripts/rea.mjs'),'doctor','--format','json'],cwd=WORK,capture_output=True,text=True,encoding='utf8',timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
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
