"""Optional original-provider calls through the installed Hermes agent, without copying it."""
import ast
import json
import re
from pathlib import Path
import threading
import time
from collections import Counter
from . import store

SERIAL = threading.Lock()
ACTIVE = Counter()
CANCELS = {}


def format_response(text, system):
    # Preserve the provider's JSON-object contract across agent tool/progress output.
    if 'JSON 객체' not in system and not re.search(r'JSON\s*(?:만|형식|only|object)', system, re.I): return text
    start = text.find('{')
    if start < 0: raise ValueError('앱이 요구한 JSON 객체가 하네스 응답에 없습니다.')
    try: value, _ = json.JSONDecoder().raw_decode(text[start:])
    except ValueError as exc: raise ValueError('하네스의 JSON 응답을 해석할 수 없습니다.') from exc
    if not isinstance(value, dict): raise ValueError('앱의 응답은 JSON 객체여야 합니다.')
    return json.dumps(value, ensure_ascii=False)


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
        if payload.get('operation') == 'settings':
            cfg = bridge.call('settings')
            return {'mode': 'hermes' if cfg.get('model') else 'rules', 'name': cfg.get('model') or '모델 미선택', 'endpoint': cfg.get('base_url', '')}
        ACTIVE[key] += 1
        CANCELS.setdefault(key, []).append(cancelled)
    session = None
    deadline = time.monotonic() + 900
    try:
        if ACTIVE[key] == 1: update(key, state='waiting', error='', session_id=None)
        while not SERIAL.acquire(timeout=.25):
            if cancelled.is_set() or time.monotonic() > deadline: raise ValueError('하네스 대기를 중단했습니다.')
        try:
            if cancelled.is_set(): raise ValueError('하네스 요청을 중단했습니다.')
            if bridge.busy_reason(): raise ValueError('Hermes가 다른 작업을 실행 중입니다. 완료 후 다시 요청하세요.')
            number = store.read(key).get('harness', {}).get('request_number', 0) + 1
            update(key, request_number=number)
            session = bridge.call('session/create', {'title': f'{record.get("title", key)} · 앱 요청 {number}'})['session']['id']
            result = bridge.call('chat', {'session_id': session, 'workspace': record['active_source'], 'message':
                'Execute this installed application request using the Hermes harness and configured tools. '
                'Preserve its required output format and owner approval/business decision rules. '
                'Use tools when needed to verify facts; never claim unperformed actions. '
                'Return only the final application response, not intermediate progress.\n\n'
                f'Application instructions:\n{system}\n\nApplication context and user request:\n{user}'})
            session = result['job']['session_id']
            update(key, state='running', session_id=session)
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
    if state.get('session_id'):
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
