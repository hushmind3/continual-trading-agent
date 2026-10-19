"""Platform adapter around the transplanted Hermes engine; no replacement agent loop."""
from __future__ import annotations

import atexit
import contextlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
import uuid

ENGINE = Path(__file__).resolve().parent
sys.path.insert(0,str(ENGINE))
from locations import ROOT, MODULE_ROOT, NODE_BIN, PYTHON
UPSTREAM = ENGINE / 'upstream'
HOME = Path(os.environ.get('HERMES_HOME') or ROOT / 'runtime/ai_agent/Hermes').resolve()
HOME.mkdir(parents=True, exist_ok=True)
# Set isolation before importing any upstream code; never inherit another Hermes install.
os.environ['HERMES_HOME'] = str(HOME)
os.environ['HERMES_RUNTIME_DIR'] = str(HOME / 'runtime')
os.environ['TERMINAL_ENV'] = 'local'
os.environ['CUA_DRIVER_RS_TELEMETRY_ENABLED'] = '0'
os.environ['HERMES_SKIP_UPDATE_CHECK'] = '1'
os.environ['HERMES_DISABLE_LAZY_INSTALLS'] = '1'
os.environ['PATH'] = str(NODE_BIN) + os.pathsep + str(PYTHON.parent) + os.pathsep + os.environ.get('PATH', '')
for _browser in (Path('C:/Program Files/Google/Chrome/Application/chrome.exe'),
                 Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')):
    if _browser.is_file():
        os.environ.setdefault('AGENT_BROWSER_EXECUTABLE_PATH', str(_browser))
        break
_driver = ROOT / 'runtime/ai_agent/Hermes/tools/cua-driver/cua-driver.exe'
if _driver.is_file():
    os.environ['HERMES_CUA_DRIVER_CMD'] = str(_driver)
sys.path.insert(0, str(UPSTREAM))
import types
for _name in ('ai_agent','ai_agent.Hermes'):
    if _name not in sys.modules:
        _package=types.ModuleType(_name);_package.__path__=[str(ENGINE.parent)] if _name.endswith('.Hermes') else []
        _package.__package__=_name;sys.modules[_name]=_package
sys.modules['ai_agent'].Hermes=sys.modules['ai_agent.Hermes']

OUTPUT = sys.stdout
sys.stdout = sys.stderr

from run_agent import AIAgent
from hermes_state import SessionDB
from ruamel.yaml import YAML
from ai_agent.Hermes.engine.execution import bind_model, context_window, request_policy, settle_review
from ai_agent.Hermes.engine.runtime_policy import model_options, save_options, configure_tools, apply_thinking, apply_response_contract, application_generation, apply_application_generation

SETTINGS = HOME / 'platform-settings.json'
DEFAULTS = {'base_url': 'http://127.0.0.1:8080/v1', 'model': '', 'api_key': '',
            'workspace': str(ROOT), 'max_iterations': 100,
            'toolsets': ['terminal', 'file', 'todo', 'skills'], 'local_model': '', 'system_prompt': '', 'read_only': False,
            'model_options': {}, 'tool_loading': 'native'}


def atomic_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def load_settings():
    return {**DEFAULTS, **(json.loads(SETTINGS.read_text(encoding='utf-8')) if SETTINGS.is_file() else {})}


def unpack(value):
    return json.loads(value) if isinstance(value, str) else value


class HermesWorker:
    def __init__(self):
        self.db = SessionDB(db_path=HOME / 'state.db')
        self.agent = None
        self.thread = None
        self.lock = threading.RLock()
        self.job = {'state': 'idle', 'session_id': None, 'text': '', 'events': [], 'error': ''}
        self.model_process = None
        self.model_log = None
        self.model_base = ''
        self.yaml = YAML(typ='safe')
        self.stopping = False
        self.approval_waiter = threading.Event()
        self.approval_result = False
        self.approval_lock = threading.Lock()
        from ai_agent.Hermes.mcp.catalog import Catalog
        self.catalog = Catalog(self)
        # AX results work with local text/tool models without a separate vision projector.
        cfg = self.native_config()
        cfg.setdefault('computer_use', {}).setdefault('capture_after_mode', 'ax')
        if not cfg.setdefault('browser', {}).get('backend'):
            cfg['browser']['backend'] = 'off'  # native agent-browser stack, not browser-use CLI
        self.write_config(cfg)
        # Original skills loader uses HERMES_HOME/skills; seed without overwriting user files.
        for source in (UPSTREAM / 'skills').rglob('*'):
            if source.is_file():
                target = HOME / 'skills' / source.relative_to(UPSTREAM / 'skills')
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)

    def idle_required(self):
        if getattr(self, 'catalog', None) and self.catalog.thread and self.catalog.thread.is_alive():
            raise ValueError('MCP 설치가 진행 중입니다. 완료 후 다시 시도하세요.')
        if self.thread and self.thread.is_alive():
            raise ValueError('에이전트가 작업 중입니다. 중지 또는 완료 후 변경하세요.')

    def event(self, name, data=None):
        # Keep output bounded; original complete messages stay in SessionDB.
        with self.lock:
            item = {'name': name, 'detail': json.dumps(data, ensure_ascii=False, default=str)[:2400] if data is not None else '', 'time': time.time()}
            self.job['events'] = (self.job['events'] + [item])[-100:]
            if name == 'tool_start':
                self.job['live_text'] = ''
                self.job['phase'] = 'tool'
            elif name == 'tool_complete':self.job['phase'] = 'generating'

    def delta(self, text, *args, **kwargs):
        if isinstance(text, str):
            with self.lock:
                self.job['text'] += text
                self.job['live_text'] = self.job.get('live_text','') + text
                self.job['phase'] = 'generating'

    def public_settings(self):
        cfg = load_settings()
        return {**cfg, **model_options(cfg,self.native_config()), 'api_key': '', 'has_api_key': bool(cfg.get('api_key')),
                'python': sys.version.split()[0], 'engine': str(UPSTREAM),
                'available_toolsets': ['terminal', 'file', 'todo', 'skills', 'browser', 'computer_use', 'memory'],
                'computer_driver_installed': _driver.is_file(),
                'browser_runtime_installed': bool(shutil.which('agent-browser') and os.environ.get('AGENT_BROWSER_EXECUTABLE_PATH'))}

    def save_settings(self, request):
        self.idle_required()
        cfg = load_settings()
        for key in DEFAULTS:
            if key=='model_options':continue
            if key in request and not (key == 'api_key' and request[key] == ''):
                cfg[key] = request[key]
        from urllib.parse import urlparse
        parsed = urlparse(str(cfg['base_url']))
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('모델 주소는 인증정보를 제외한 http:// 또는 https:// 주소여야 합니다.')
        cfg['base_url'] = cfg['base_url'].rstrip('/')
        if not isinstance(cfg['system_prompt'],str):
            raise ValueError('시스템 프롬프트는 문자열이어야 합니다.')
        if not isinstance(cfg['read_only'],bool):raise ValueError('읽기 전용 설정은 참/거짓이어야 합니다.')
        workspace = Path(str(cfg['workspace'])).expanduser().resolve()
        if not workspace.is_dir():
            raise ValueError('작업 폴더가 존재하지 않습니다.')
        cfg['workspace'] = str(workspace)
        cfg['max_iterations'] = int(cfg['max_iterations'])
        if not 1 <= cfg['max_iterations'] <= 10000:
            raise ValueError('최대 작업 반복 횟수는 1~10000입니다.')
        if not isinstance(cfg['toolsets'], list) or any(t not in self.public_settings()['available_toolsets'] for t in cfg['toolsets']):
            raise ValueError('지원하지 않는 도구 묶음입니다.')
        cfg=save_options(cfg,request)
        atomic_json(SETTINGS, cfg)
        return self.public_settings()

    def model_client(self, request=None):
        from openai import OpenAI
        cfg = load_settings()
        request = request or {}
        return OpenAI(base_url=request.get('base_url') or cfg['base_url'],
                      api_key=request.get('api_key') or cfg.get('api_key') or 'local', timeout=12, max_retries=0)

    def native_config(self):
        path = HOME / 'config.yaml'
        return (self.yaml.load(path.read_text(encoding='utf-8')) or {}) if path.exists() else {}

    def write_config(self, cfg):
        path = HOME / 'config.yaml'
        temporary = path.with_suffix('.tmp')
        with temporary.open('w', encoding='utf-8') as handle:
            self.yaml.dump(cfg, handle)
        temporary.replace(path)
        # Native load_config caches by file signature; atomic replacement invalidates it.

    def sessions(self):
        return self.db.list_sessions_rich(limit=100, min_message_count=0, order_by_last_active=True)

    def session(self, session_id):
        row = self.db.get_session(session_id)
        if not row:
            raise ValueError('세션을 찾을 수 없습니다.')
        return {'session': row, 'messages': self.db.get_messages_as_conversation(session_id)}

    def create_session(self, request):
        session_id = uuid.uuid4().hex
        cfg = load_settings()
        self.db.create_session(session_id, 'platform', model=cfg['model'] or None)
        title = str(request.get('title') or '새 대화')[:100]
        self.db.set_session_title(session_id, self.db.get_next_title_in_lineage(title))
        return self.session(session_id)

    def start_chat(self, request):
        request = dict(request)
        raw = str(request.get('message') or '').strip()
        if raw in {'/stop','/goal pause','/loop pause','/loop stop'}: return self.stop()
        if raw in {'/goal resume','/loop resume'}:
            from ai_agent.Hermes.chat.autonomy import snapshot
            mode='goal' if raw.startswith('/goal') else 'loop'
            state=snapshot(str(request.get('session_id') or '')).get(mode)
            if not state:raise ValueError('재개할 작업이 없습니다.')
            request.update(mode=mode,resume=True,message=state.get('goal') or state.get('prompt'))
        elif raw.startswith('/goal '):
            request.update(mode='goal',message=raw[6:].removeprefix('set '))
        elif raw.startswith('/loop '):
            from hermes_cli.loops import parse_loop_args
            parsed = parse_loop_args(raw[6:])
            if parsed.pop('error',None):raise ValueError('반복 명령을 확인하세요. 예: /loop 5m 작업내용')
            request.update(mode='loop',message=parsed.pop('prompt'), **parsed)
        self.idle_required()
        cfg = request_policy(load_settings(), request)
        application_prompt = request.get('application_system_prompt', '')
        if not isinstance(application_prompt, str) or len(application_prompt) > 50000:
            raise ValueError('앱 시스템 지침은 50,000자 이하 문자열이어야 합니다.')
        cfg['application_system_prompt'] = application_prompt
        response_format = request.get('application_response_format', '')
        if response_format not in ('', 'json_object'): raise ValueError('앱 응답 형식을 확인하세요.')
        cfg['application_response_format'] = response_format
        plan_only = request.get('application_plan_only', False)
        if not isinstance(plan_only, bool): raise ValueError('앱 계획 단계는 참/거짓이어야 합니다.')
        cfg['application_plan_only'] = plan_only
        cfg['application_generation'] = application_generation(request.get('application_generation', {}))
        if request.get('workspace'):
            selected = Path(str(request['workspace'])).expanduser().resolve()
            if not selected.is_dir():raise ValueError('선택한 프로젝트 폴더가 없습니다.')
            cfg['workspace'] = str(selected)
        if not cfg['model']:
            raise ValueError('모델 설정에서 모델을 선택하고 저장하세요.')
        if cfg.get('local_model') and self.status()['local_model']['state'] != 'ready':
            raise ValueError('모델 탭에서 로컬 모델을 불러온 뒤 대화를 시작하세요.')
        prompt = str(request.get('message') or '').strip()
        if not prompt:
            raise ValueError('메시지를 입력하세요.')
        if len(prompt) > 200000:
            raise ValueError('메시지가 너무 깁니다.')
        session_id = str(request.get('session_id') or '')
        row = self.session(session_id) if session_id else self.create_session({'title': prompt[:60]})
        session_id = row['session']['id']
        if str(row['session'].get('title') or '').startswith('새 대화'):
            self.db.set_session_title(session_id, self.db.get_next_title_in_lineage(prompt[:60]))
        history = row['messages']
        with self.lock:
            self.job = {'state': 'starting', 'session_id': session_id, 'text': '', 'events': [], 'error': '', 'started_at': time.time()}
        self.thread = threading.Thread(target=self.run_chat, args=(cfg, session_id, prompt, history, request), daemon=True)
        self.thread.start()
        return self.status()

    def run_chat(self, cfg, session_id, prompt, history, request=None):
        from tools.approval_context import set_hermes_interactive_context, reset_hermes_interactive_context
        interactive_token = set_hermes_interactive_context(True)
        completion = {}
        try:
            # Several upstream file/skill helpers use process cwd as their final fallback.
            # This worker owns a single active task, so pin all helpers to the selected workspace.
            os.chdir(cfg['workspace'])
            from tools.terminal_tool import set_approval_callback
            from tools.computer_use.tool import set_approval_callback as set_computer_approval
            set_approval_callback(self.approve)
            set_computer_approval(self.approve)
            os.environ['TERMINAL_CWD'] = cfg['workspace']
            self.event('starting', {'model': cfg['model'], 'workspace': cfg['workspace']})
            from tools.mcp_tool_discovery import get_registered_mcp_server_names
            from ai_agent.Hermes.chat.desktop_browser import bind
            bind(self)
            from tools import tool_search
            tool_search._DIRECT_SURFACE_TOOLSETS = tool_search._DIRECT_SURFACE_TOOLSETS | {'computer_use'}
            toolsets = list(cfg['toolsets']) + ['mcp-' + name for name in get_registered_mcp_server_names()]
            if cfg.get('read_only'):toolsets=['file']
            configure_tools(self,'eager' if cfg.get('read_only') else cfg.get('tool_loading','native'))
            self.agent = AIAgent(
                model=cfg['model'], base_url=cfg['base_url'], api_key=cfg.get('api_key') or 'local',
                provider='custom', api_mode='chat_completions', quiet_mode=True,
                session_id=session_id, session_db=self.db, platform='platform',
                enabled_toolsets=toolsets, max_iterations=cfg['max_iterations'], cwd=cfg['workspace'],
                # Only read-only mode suppresses review writes; normal runs use upstream defaults.
                skip_background_review=bool(cfg.get('read_only')),
                ephemeral_system_prompt=(
                    f'The selected working directory is {cfg["workspace"]}. '
                    'Resolve relative file paths against this exact directory. '
                    'Never invent or substitute another working directory. '
                    'Use tool_search then tool_describe to discover configured deferred tools '
                    'before claiming a browser, desktop, or MCP tool is unavailable. '
                    'Report success only when tool results confirm it. '
                    'When reporting a document or code file, include a Markdown link to its exact local path so the user can open it in the platform. '
                    'The platform displays Markdown links and captures write_file results as clickable documents. For HTML reports use self-contained static HTML with inline CSS; scripts and external resources are blocked. Do not open Notepad or a browser just to display a report in this chat. '
                    f'This host is Windows. Installed browser executable: {os.environ.get("AGENT_BROWSER_EXECUTABLE_PATH","not detected")}. '
                    'The terminal shell may be Git Bash: ps/which cannot reliably detect Windows applications. '
                    'When asked to open visible Chrome/Edge, your FIRST tool call MUST be desktop_browser, which launches detached without shell quoting. '
                    'For other visible desktop apps, use PowerShell Start-Process with its exact executable path and return immediately. '
                    'Do not launch GUI apps as blocking terminal commands or wrap them in timeout; terminal cleanup can close their windows. '
                    'Use computer_use capture in ax mode to verify the visible window once. '
                    'Once the requested app is open, leave it open and finish. Do not close, relaunch or keep polling it. '
                    'If the user closes the app, do not reopen it without a new request. '
                    'browser_* tools control a separate automation browser; they do not prove the user-visible desktop app is open.'
                    + ('\nRead-only code analysis: only read_file and search_files inside the selected workspace are permitted. Do not request editing, terminal, code execution, MCP, delegation or desktop tools.' if cfg.get('read_only') else '')
                    + ('\n\nAdditional user-configured system instructions:\n'+cfg['system_prompt'] if cfg.get('system_prompt') else '')
                    + ('\n\nApplication role and response contract for this request:\n'+cfg['application_system_prompt']+
                       '\nPreserve owner approval requirements. Use configured tools only when the current request needs them; '
                       'never execute historical requests from application context. Return only the final application response in its required format.'
                       if cfg.get('application_system_prompt') else '')),
                stream_delta_callback=self.delta, event_callback=self.event,
                status_callback=lambda *args, **kw: self.event('status', args),
                tool_start_callback=lambda *args, **kw: self.event('tool_start', args),
                tool_complete_callback=lambda *args, **kw: self.event('tool_complete', args),
                clarify_callback=self.clarify,
            )
            apply_thinking(self.agent,model_options(cfg,self.native_config()),bool(cfg.get('local_model')))
            apply_response_contract(self.agent, cfg.get('application_response_format'), cfg.get('application_plan_only', False))
            apply_application_generation(self.agent, cfg.get('application_generation', {}))
            if cfg.get('read_only'):
                from ai_agent.Hermes.chat.read_only import bind as bind_read_only
                bind_read_only(self.agent,cfg['workspace'],lambda reason:self.event('permission_denied',{'message':reason}),(request or {}).get('attachments',[]))
            with self.lock:
                self.job['state'] = 'running'
            if self.stopping:
                self.agent.interrupt(hard_cancel=True)
            from ai_agent.Hermes.chat.autonomy import run
            result = run(self,self.agent,cfg,session_id,prompt,history,request or {})
            if result.get('error'):
                raise RuntimeError(str(result['error']))
            autonomy = self.job.get('autonomy') or {}
            incomplete = result.get('failed') or not result.get('completed', True)
            state = 'stopped' if self.stopping else 'paused' if autonomy.get('status') == 'paused' or incomplete else 'complete'
            completion = dict(state=state, text=result.get('final_response') or self.job['text'], finished_at=time.time())
            if incomplete and not self.stopping:completion['error'] = '작업이 완료되지 않았습니다. '+str(result.get('turn_exit_reason') or '도구 실행 결과를 확인하세요.')
            if getattr(self.agent,'_read_only_denials',None):
                completion['error']=(completion.get('error','')+' '+self.agent._read_only_denials[-1]).strip()
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            completion = dict(state='stopped' if self.stopping else 'failed', error=str(exc), finished_at=time.time())
        finally:
            if self.agent:
                settle_review(self)
                from ai_agent.Hermes.chat.telemetry import update
                with self.lock:self.job['metrics'] = update(self)
                with contextlib.suppress(Exception): self.agent.close()
            self.agent = None
            if self.stopping:
                completion['state'] = 'stopped'
            completion['finished_at'] = time.time()
            self.stopping = False
            reset_hermes_interactive_context(interactive_token)
            os.chdir(ROOT)
            with self.lock:
                self.job.update(completion)

    def status(self):
        from ai_agent.Hermes.chat.telemetry import update
        with self.lock:
            self.job['metrics'] = update(self)
        with self.lock:
            job = {**self.job, 'events': list(self.job['events'])}
        model = {'running': bool(self.model_process and self.model_process.poll() is None), 'base_url': self.model_base, 'state': 'idle'}
        if model['running']:
            from urllib.request import urlopen
            model['state'] = 'loading'
            try:
                with urlopen(self.model_base.removesuffix('/v1') + '/health', timeout=.4) as response:
                    if response.status == 200: model['state'] = 'ready'
            except OSError: pass
        if self.model_process and self.model_process.poll() is not None:
            model['state'] = 'failed'
            model['error'] = '로컬 모델 프로세스가 종료됐습니다. local-model.log를 확인하세요.'
        installing=getattr(getattr(self,'catalog',None),'thread',None)
        return {'job': job, 'local_model': model,
            'mcp_installation':{'state':'running' if installing and installing.is_alive() else 'idle'}}

    def stop(self):
        if self.thread and self.thread.is_alive():
            self.stopping = True
            self.approval_result = False
            self.approval_waiter.set()
            if self.agent:
                self.agent.interrupt(hard_cancel=True)
            with self.lock:
                self.job['state'] = 'stopping'
        return self.status()

    def approve(self, *args, **kwargs):
        with self.approval_lock:
            self.approval_result = False
            self.approval_waiter.clear()
            with self.lock:
                self.job['approval'] = {'kind': 'tool', 'detail': json.dumps({'args': args, 'kwargs': kwargs}, ensure_ascii=False, default=str)[:6000]}
            if not self.stopping: self.approval_waiter.wait(timeout=300)
            with self.lock:
                self.job.pop('approval', None)
            return 'once' if self.approval_result and not self.stopping else 'deny'

    def clarify(self, *args, **kwargs):
        self.approval_waiter.clear()
        self.approval_result = ''
        with self.lock:
            self.job['approval'] = {'kind': 'question', 'detail': json.dumps({'args': args, 'kwargs': kwargs}, ensure_ascii=False, default=str)[:6000]}
        self.approval_waiter.wait(timeout=300)
        with self.lock:
            self.job.pop('approval', None)
        return str(self.approval_result or '사용자가 응답하지 않았습니다.')

    def load_model(self, request):
        self.idle_required()
        path = Path(str(request.get('path') or '')).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() != '.gguf':
            raise ValueError('존재하는 GGUF 모델 파일을 선택하세요. 다른 형식은 해당 모델 실행기의 API 주소를 연결하세요.')
        executable = ROOT / 'runtime/shared/engines/llama.cpp/llama-server.exe'
        if not executable.is_file():
            raise ValueError('설치된 llama-server 실행기를 찾을 수 없습니다.')
        alias = path.parent.name if path.stem.upper() in {'GGUF', 'MODEL'} else path.stem
        native = self.native_config()
        context_length = model_options({**load_settings(),'model':alias},native)['context_length']
        self.unload_model()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        self.model_log = (HOME / 'local-model.log').open('a', encoding='utf-8')
        self.model_process = subprocess.Popen(
            [str(executable), '--model', str(path), '--host', '127.0.0.1', '--port', str(port),
             '--n-gpu-layers', 'auto', '--ctx-size', str(context_length or 0), '--parallel', '1',
             '--threads', '2', '--threads-batch', '2',
             '-fa', 'on', '-ctk', 'q8_0', '-ctv', 'q8_0',
             '--jinja', '--alias', alias],
            cwd=path.parent, stdout=self.model_log, stderr=self.model_log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        self.model_base = f'http://127.0.0.1:{port}/v1'
        self._slot_sample=None
        with self.lock:self.job.pop('metrics',None)
        self.write_config(bind_model(native, alias, self.model_base, context_length))
        self.save_settings({'base_url': self.model_base, 'model': alias, 'local_model': str(path)})
        return self.status()

    def unload_model(self):
        self.idle_required()
        if self.model_process and self.model_process.poll() is None:
            self.model_process.terminate()
            try: self.model_process.wait(timeout=8)
            except subprocess.TimeoutExpired: self.model_process.kill()
        self.model_process = None
        if self.model_log:
            self.model_log.close()
            self.model_log = None
        return self.status()

    def mcp(self):
        from tools.mcp_tool_discovery import get_mcp_status
        from tools import mcp_tool
        cfg = self.native_config().get('mcp_servers', {})
        rows = get_mcp_status(configured=cfg)
        for row in rows:
            row['tool_names'] = sorted(name for name, server in mcp_tool._mcp_tool_server_names.items() if server == row['name'])
        return {'servers': cfg, 'status': rows}

    def mcp_save(self, request):
        self.idle_required()
        servers = request.get('servers', {})
        if not isinstance(servers, dict):
            raise ValueError('MCP 서버 설정은 이름을 키로 하는 JSON 객체여야 합니다.')
        for name, server in servers.items():
            if not name or not isinstance(server, dict) or not (server.get('command') or server.get('url')):
                raise ValueError(f'{name}: command 또는 url이 필요합니다.')
            if 'args' in server and (not isinstance(server['args'], list) or any(not isinstance(arg, str) for arg in server['args'])):
                raise ValueError(f'{name}: args는 문자열 배열이어야 합니다.')
        cfg = self.native_config()
        cfg['mcp_servers'] = servers
        self.write_config(cfg)
        from tools.mcp_tool_lifecycle import shutdown_mcp_servers
        shutdown_mcp_servers()
        return self.mcp()

    def execute(self, operation, payload):
        if operation == 'autonomy':
            from ai_agent.Hermes.chat.autonomy import snapshot
            self.session(str(payload.get('id') or ''))
            running = self.thread and self.thread.is_alive() and self.job.get('session_id') == payload['id']
            return snapshot(str(payload['id']), recover=not running)
        if operation == 'mcp/project':
            from ai_agent.Hermes.mcp.project_links import synchronize
            return synchronize(self, payload)
        if operation == 'mcp/catalog': return self.catalog.listing()
        if operation == 'mcp/catalog/install': return self.catalog.install(payload)
        if operation in {'skills','skill/toggle','skill/content','skill/save'}:
            from ai_agent.Hermes.skills.catalog import execute
            return execute(self,operation,payload)
        if operation == 'engine/info':
            return {'root': str(UPSTREAM), 'modules': {name: str(Path(module.__file__).resolve())
                for name, module in tuple(sys.modules.items()) if getattr(module, '__file__', None)
                and name.split('.')[0] in {'agent', 'tools', 'hermes_cli', 'run_agent', 'model_tools', 'pm', 'gateway'}}}
        if operation == 'settings': return self.public_settings()
        if operation == 'settings/save': return self.save_settings(payload)
        if operation == 'models':
            with self.model_client(payload) as client:
                return {'models': [{'id': row.id} for row in client.models.list().data]}
        if operation == 'models/local':
            model_root = Path.home() / 'Desktop/모델'
            return {'root': str(model_root), 'models': [{'path': str(path), 'name': path.relative_to(model_root).as_posix(), 'bytes': path.stat().st_size}
                for path in sorted(model_root.rglob('*.gguf')) if path.is_file()] if model_root.is_dir() else []}
        if operation == 'model/load': return self.load_model(payload)
        if operation == 'model/unload': return self.unload_model()
        if operation == 'sessions': return self.sessions()
        if operation == 'session/create': return self.create_session(payload)
        if operation == 'session': return self.session(str(payload.get('id') or ''))
        if operation == 'session/rename':
            session_id = str(payload.get('id') or '')
            title = ' '.join(str(payload.get('title') or '').split())
            if not title or len(title) > 120 or any(ord(char) < 32 for char in title):
                raise ValueError('대화 제목은 1~120자로 입력하세요.')
            self.session(session_id)
            self.db.set_session_title(session_id, title)
            return self.sessions()
        if operation == 'session/archive':
            if self.thread and self.thread.is_alive() and self.job['session_id'] == payload.get('id'):
                raise ValueError('작업 중인 세션은 보관할 수 없습니다.')
            self.session(payload['id'])
            self.db.set_session_archived(payload['id'], True)
            return self.sessions()
        if operation == 'chat': return self.start_chat(payload)
        if operation == 'status': return self.status()
        if operation == 'stop': return self.stop()
        if operation == 'answer':
            if not self.job.get('approval'):
                raise ValueError('응답을 기다리는 요청이 없습니다.')
            self.approval_result = str(payload.get('text') or '') if self.job['approval']['kind'] == 'question' else bool(payload.get('allow'))
            self.approval_waiter.set()
            return {'accepted': True}
        if operation == 'mcp': return self.mcp()
        if operation == 'mcp/save': return self.mcp_save(payload)
        if operation == 'mcp/connect':
            self.idle_required()
            from tools.mcp_tool_discovery import discover_mcp_tools
            discover_mcp_tools()
            return self.mcp()
        if operation == 'skills':
            from tools.skills_tool import skills_list
            return unpack(skills_list())
        if operation == 'skill':
            from tools.skills_tool import skill_view
            return unpack(skill_view(str(payload.get('name') or ''), preprocess=False))
        if operation == 'shutdown':
            self.close()
            return {'closed': True}
        raise ValueError('지원하지 않는 Hermes 작업입니다.')

    def close(self):
        self.stop()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=4)
        with contextlib.suppress(Exception): self.unload_model()
        from tools.mcp_tool_lifecycle import shutdown_mcp_servers
        with contextlib.suppress(Exception): shutdown_mcp_servers()
        with contextlib.suppress(Exception): self.db.close()


def main():
    worker = HermesWorker()
    atexit.register(worker.close)
    for line in sys.stdin:
        request = {}
        try:
            request = json.loads(line)
            result = worker.execute(request['operation'], request.get('payload') or {})
            message = {'id': request['id'], 'result': result}
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            message = {'id': request.get('id'), 'error': str(exc)}
        OUTPUT.write(json.dumps(message, ensure_ascii=False, default=str) + '\n')
        OUTPUT.flush()
        if request.get('operation') == 'shutdown':
            break


if __name__ == '__main__':
    main()
