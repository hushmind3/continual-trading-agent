"""Optional original-provider calls through the installed Hermes agent, without copying it."""
import ast
import json
from pathlib import Path
import threading
import time
import uuid
from collections import Counter
from . import store
from .harness_prompt import message_for, requires_json, stage_for
from .execution_watch import ProgressWindow, wait_owned

SERIAL = threading.Lock()
ACTIVE = Counter()
CANCELS = {}


def format_response(text, system):
    # Preserve the provider's JSON-object contract across agent tool/progress output.
    if not requires_json(system): return text
    decoder = json.JSONDecoder()
    # A native streaming retry can leave an unfinished prefix before the completed final object.
    # Use a genuinely decoded object; never close braces or invent a plan from plain prose.
    for start, char in enumerate(text):
        if char != '{': continue
        try: value, _ = decoder.raw_decode(text, start)
        except ValueError: continue
        if not isinstance(value, dict): continue
        if '"reply"' in system and not isinstance(value.get('reply'), str): continue
        return json.dumps(value, ensure_ascii=False)
    raise ValueError('앱이 요구한 완전한 JSON 객체가 하네스 응답에 없습니다.')


def discover(source):
    file = Path(source) / 'ai_provider.py'
    if not file.is_file(): return ''
    try: tree = ast.parse(file.read_text(encoding='utf-8-sig'))
    except (OSError, SyntaxError): return ''
    return 'ai_provider:compose' if any(isinstance(n, ast.AsyncFunctionDef) and n.name == 'compose' and
        [a.arg for a in n.args.args][:2] == ['system', 'user'] for n in tree.body) else ''


def configure(record, enabled):
    if not isinstance(enabled, bool): raise ValueError('하네스 선택은 참/거짓이어야 합니다.')
    source = Path(record.get('active_source') or '')
    entry = discover(source)
    if enabled and (record.get('adapter', {}).get('kind') != 'fastapi' or not entry):
        raise ValueError('이 앱의 모델 호출 연결 규격을 아직 지원하지 않습니다.')
    record['harness'] = {**record.get('harness', {}), 'enabled': enabled, 'entry': entry, 'state': 'idle', 'error': ''}
    return record


def busy_reason():
    with store.LOCK:
        if ACTIVE:return '외부 앱에서 실행 중인 Hermes 하네스'
    from ai_agent.Hermes.engine.bridge import bridge
    if bridge.process and bridge.process.poll() is None:
        try:
            job=bridge.call('status')['job']
            if (job.get('company_id') or job.get('company_job_id')) and job.get('state') in ('starting','running','stopping'):
                return '연결된 조직에서 실행 중인 Hermes 작업'
        except (RuntimeError,ValueError):return 'Hermes 실행 상태 확인 실패; 변경 보류'
    return ''


def measured_job(job):
    """Keep actual owned measurements without storing tool payloads."""
    return {key: job[key] for key in ('state', 'session_id', 'application', 'metrics', 'started_at', 'error') if key in job}


def update(key, **values):
    with store.LOCK:
        record = store.read(key)
        record['harness'] = {**record.get('harness', {}), **values}
        store.save(record)


def execute(key, payload, cancelled):
    from ai_agent.Hermes.engine.bridge import bridge
    system, user = payload.get('system', ''), payload.get('user', '')
    if not isinstance(system, str) or not isinstance(user, str) or len(system) + len(user) > 180000:
        raise ValueError('앱의 하네스 요청이 올바르지 않습니다.')
    with store.LOCK:
        record = store.read(key)
        if not record.get('harness', {}).get('enabled'): raise ValueError('앱의 Hermes 연결이 꺼져 있습니다.')
        if payload.get('operation') == 'settings':
            cfg = bridge.call('settings')
            return {'mode': 'hermes' if cfg.get('model') else 'rules', 'name': cfg.get('model') or '모델 미선택', 'endpoint': cfg.get('base_url', '')}
        ACTIVE[key] += 1
        CANCELS.setdefault(key, []).append(cancelled)
    session = None
    try:
        phase = {**stage_for(system, user), 'started_at': time.time()}
        if ACTIVE[key] == 1: update(key, state='waiting', error='', session_id=None, last_job=None, phase=phase)
        while not SERIAL.acquire(timeout=.25):
            if cancelled.is_set(): raise ValueError('하네스 대기를 중단했습니다.')
        try:
            if cancelled.is_set(): raise ValueError('하네스 요청을 중단했습니다.')
            waiting = ProgressWindow()
            while bridge.busy_reason():
                if cancelled.is_set(): raise ValueError('하네스 대기를 중단했습니다.')
                if waiting.observe(bridge.call('status')['job']):
                    raise ValueError('다른 Hermes 작업의 진행을 기다리는 시간이 초과됐습니다. 해당 작업은 중지하지 않았습니다.')
                cancelled.wait(.4)
            plan_only = requires_json(system)
            generation = {}
            workspace = record['active_source']
            if payload.get('workspace'):
                from .store import owned,project_folder
                candidate=Path(payload['workspace']).resolve()
                base=project_folder(record).resolve()
                if not candidate.is_relative_to(base) or not candidate.is_dir(): raise ValueError('앱 소유 작업 폴더가 아닙니다.')
                workspace=str(candidate)
            result = bridge.call('chat', {'application_request': True, 'workspace': workspace,
                'application_system_prompt': system, 'application_plan_only': plan_only,
                'application_context_scope': 'native' if phase['kind'] == 'task' else 'focused_discussion',
                'application_generation': generation,
                'application_response_format': 'json_object' if plan_only else '', 'message': message_for(user)})
            session = result['job']['session_id']
            update(key, state='running', session_id=session, phase={**phase, 'started_at': time.time()})
            job = wait_owned(bridge, session, cancelled, payload.get('execution') is True)
            if job['state'] != 'complete' or job.get('error'):
                raise ValueError(job.get('error') or '하네스가 작업을 완료하지 못했습니다.')
            text = job.get('text', '').strip()
            if not text: raise ValueError('하네스의 최종 응답이 비었습니다.')
            text = format_response(text, system)
            update(key, state='complete', last_job=measured_job(job), finished_at=time.time())
            return text
        finally: SERIAL.release()
    except Exception as exc:
        update(key, state='failed', error=str(exc), finished_at=time.time())
        raise
    finally:
        with store.LOCK:
            ACTIVE[key] -= 1
            if not ACTIVE[key]: del ACTIVE[key]
            CANCELS[key].remove(cancelled)
            if not CANCELS[key]: del CANCELS[key]


def status(key):
    record = store.read(key); state = record.get('harness', {})
    if record.get('stage') == 'ready' and state.get('enabled') and record.get('workspace_ui', {}).get('native'):
        from ai_agent.Hermes.engine.bridge import bridge
        session = uuid.uuid5(uuid.NAMESPACE_URL, 'platform-company:' + key).hex
        job = bridge.call('status')['job']
        owned = job.get('session_id') == session
        return {'enabled': True, 'native': True, 'session_id': session,
                'state': job['state'] if owned else 'idle', 'job': job if owned else None,
                'phase': {'kind': 'task', 'role': 'CEO', 'label': 'Hermes 총괄'}}
    if state.get('state') in ('running', 'waiting') and key not in ACTIVE:
        update(key, state='failed', error='플랫폼 연결이 중단됐습니다. 앱에서 다시 요청하세요.')
        state = store.read(key)['harness']
    result = dict(state)
    if state.get('enabled') and state.get('state') in ('complete', 'failed') and state.get('last_job'):
        result['job'] = {**state['last_job'], 'events': []}
    if state.get('enabled') and state.get('session_id'):
        from ai_agent.Hermes.engine.bridge import bridge
        job = bridge.call('status')['job']
        if job.get('session_id') == state['session_id']:
            result['job'] = job
            if job.get('state') in ('complete', 'failed', 'stopped') and measured_job(job) != state.get('last_job'):
                update(key, last_job=measured_job(job))
    return result


def control(key, request):
    from ai_agent.Hermes.engine.bridge import bridge
    state = status(key)
    if state.get('native'):
        job = state.get('job')
        active = job and job.get('state') in ('starting','running','stopping')
        if request.get('action') == 'stop':
            if not active:return {'requested':False}
            bridge.call('stop', {'session_id': state['session_id']})
            return {'requested':True}
        if request.get('action') == 'answer' and active and job.get('approval'):
            return bridge.call('answer', {'allow': request.get('allow') is True, 'text': str(request.get('text') or '')})
        raise ValueError('이 조직에서 응답할 실행 요청이 없습니다.')
    if request.get('action') == 'stop':
        with store.LOCK:
            for event in CANCELS.get(key, []): event.set()
        return {'requested': key in ACTIVE}
    if key not in ACTIVE or not state.get('job') or state['job']['state'] not in ('starting', 'running', 'stopping'):
        raise ValueError('이 앱에서 실행 중인 하네스 작업이 없습니다.')
    if request.get('action') == 'answer': return bridge.call('answer', {'allow': request.get('allow') is True, 'text': str(request.get('text') or '')})
    raise ValueError('지원하지 않는 하네스 동작입니다.')
