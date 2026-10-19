"""Optional original-provider calls through the installed Hermes agent, without copying it."""
import ast
import json
from pathlib import Path
import threading
import time
from collections import Counter
from . import store
from .harness_prompt import message_for, requires_json, stage_for

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
    with store.LOCK: return '외부 앱에서 실행 중인 Hermes 하네스' if ACTIVE else ''


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
        if record.get('repository', '').lower() == 'hushmind3/project-zero':
            from .project_zero import provider_system
            from .project_zero_business import discussion_context
            system = provider_system(system)
            system,user = discussion_context(system,user,payload.get('context_scope'))
        if payload.get('operation') == 'settings':
            cfg = bridge.call('settings')
            return {'mode': 'hermes' if cfg.get('model') else 'rules', 'name': cfg.get('model') or '모델 미선택', 'endpoint': cfg.get('base_url', '')}
        ACTIVE[key] += 1
        CANCELS.setdefault(key, []).append(cancelled)
    session = None
    deadline = time.monotonic() + 900
    try:
        phase = {**stage_for(system, user), 'started_at': time.time()}
        if ACTIVE[key] == 1: update(key, state='waiting', error='', session_id=None, phase=phase)
        while not SERIAL.acquire(timeout=.25):
            if cancelled.is_set() or time.monotonic() > deadline: raise ValueError('하네스 대기를 중단했습니다.')
        try:
            if cancelled.is_set(): raise ValueError('하네스 요청을 중단했습니다.')
            if bridge.busy_reason(): raise ValueError('Hermes가 다른 작업을 실행 중입니다. 완료 후 다시 요청하세요.')
            number = store.read(key).get('harness', {}).get('request_number', 0) + 1
            update(key, request_number=number)
            session = bridge.call('session/create', {'title': f'{record.get("title", key)} · 앱 요청 {number}'})['session']['id']
            plan_only = record.get('repository', '').lower() == 'hushmind3/project-zero' and (requires_json(system) or phase['kind'] in ('meeting','summary'))
            generation = {}
            if record.get('repository', '').lower() == 'hushmind3/project-zero':
                generation = {'temperature': .3}
                if payload.get('max_tokens') is not None: generation['max_tokens'] = payload['max_tokens']
            result = bridge.call('chat', {'session_id': session, 'workspace': record['active_source'],
                'application_system_prompt': system,
                'application_plan_only': plan_only,
                'application_context_scope': payload.get('context_scope', 'native') if record.get('repository','').lower()=='hushmind3/project-zero' else 'native',
                'application_generation': generation,
                'application_response_format': 'json_object' if requires_json(system) and plan_only else '', 'message': message_for(user)})
            session = result['job']['session_id']
            update(key, state='running', session_id=session, phase={**phase, 'started_at': time.time()})
            while True:
                job = bridge.call('status')['job']
                if job.get('session_id') != session: raise ValueError('하네스 작업의 세션이 바뀌었습니다.')
                if cancelled.is_set() or time.monotonic() > deadline:
                    bridge.call('stop'); raise ValueError('앱의 하네스 실행을 중단했습니다.')
                if job['state'] not in ('starting', 'running', 'stopping'):
                    if job['state'] != 'complete' or job.get('error'):
                        raise ValueError(job.get('error') or '하네스가 작업을 완료하지 못했습니다.')
                    text = job.get('text', '').strip()
                    if not text: raise ValueError('하네스의 최종 응답이 비었습니다.')
                    text = format_response(text, system)
                    update(key, state='complete', finished_at=time.time())
                    return text
                cancelled.wait(.4)
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
    if state.get('state') in ('running', 'waiting') and key not in ACTIVE:
        update(key, state='failed', error='플랫폼 연결이 중단됐습니다. 앱에서 다시 요청하세요.')
        state = store.read(key)['harness']
    result = dict(state)
    if state.get('enabled') and state.get('session_id'):
        from ai_agent.Hermes.engine.bridge import bridge
        job = bridge.call('status')['job']
        if job.get('session_id') == state['session_id']: result['job'] = job
    return result


def control(key, request):
    from ai_agent.Hermes.engine.bridge import bridge
    state = status(key)
    if request.get('action') == 'stop':
        with store.LOCK:
            for event in CANCELS.get(key, []): event.set()
        return {'requested': key in ACTIVE}
    if key not in ACTIVE or not state.get('job') or state['job']['state'] not in ('starting', 'running', 'stopping'):
        raise ValueError('이 앱에서 실행 중인 하네스 작업이 없습니다.')
    if request.get('action') == 'answer': return bridge.call('answer', {'allow': request.get('allow') is True, 'text': str(request.get('text') or '')})
    raise ValueError('지원하지 않는 하네스 동작입니다.')
