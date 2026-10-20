"""Live organizational discussion using native Hermes child agents and existing records."""
import json
import threading
import time
import uuid

SCHEMA = {'name': 'team_meeting', 'description': 'Run a REAL live discussion. start registers the CURRENT requested topic immediately. speak calls ONE independent staff agent with its persona and previous actual statements; choose the next role/focus from the discussion, and call a role again to answer objections. finish concludes after at least two roles; optionally submit a business proposal for OWNER APPROVAL. Never create products or approve a proposal during discussion.',
 'parameters': {'type': 'object', 'properties': {
  'action': {'type': 'string', 'enum': ['start','speak','finish']},
  'topic': {'type': 'string', 'description': 'The current user-requested agenda, never an unrelated old project'},
  'meeting_id': {'type': 'string'}, 'role': {'type': 'string', 'description': 'Choose a role returned by start'},
  'focus': {'type': 'string', 'description': 'Specific question or objection for this speaker'},
  'summary': {'type': 'string', 'description': 'Short conclusion, disagreements and missing evidence'},
  'proposal': {'type': 'object', 'properties': {'problem': {'type':'string'}, 'product': {'type':'string'}, 'validation': {'type':'string'}, 'target_customer': {'type':'string'}, 'price': {'type':'string'}}, 'required':['problem','product','validation'], 'additionalProperties':False}},
  'required':['action'], 'additionalProperties':False}}


def records(worker, command):
    from .company import execute
    result = json.loads(execute(command))
    if result.get('error'): raise ValueError(result.get('detail') or result['error'])
    return result


def publish(worker, **values):
    with worker.lock:
        worker.job['meeting'] = {**worker.job.get('meeting', {}), **values}


def run(worker, args):
    if not getattr(worker, 'company_link', None): return json.dumps({'error':'조직 총괄 대화에서 회의를 시작하세요.'}, ensure_ascii=False)
    if not hasattr(worker, '_meeting_lock'): worker._meeting_lock = threading.RLock()
    try:
        with worker._meeting_lock:
            action = args.get('action')
            if action == 'start':
                item = records(worker, {'action':'meeting_resume', 'meeting_id':args['meeting_id']} if args.get('meeting_id') else {'action':'meeting_start', 'title':args.get('topic')})
                publish(worker, id=item['meeting_id'], company_id=worker.company_link['id'], topic=item['topic'], run_id=worker.job.get('owner_request_id',''), status='running', role='', text='', turn_id='', turn_status='', venture_id='')
                owner_message(worker, worker.job.get('owner_message',''), 'owner-'+worker.job.get('owner_request_id',uuid.uuid4().hex))
                worker.event('meeting_started', {'id':item['meeting_id'], 'topic':item['topic']})
                return json.dumps({'meeting_id':item['meeting_id'], 'topic':item['topic'], 'roles':item['roles'], 'instruction':'Choose a relevant role and call speak. Do not call company_records meeting or generate minutes yourself.'}, ensure_ascii=False)
            key = args.get('meeting_id') or worker.job.get('meeting', {}).get('id')
            item = records(worker, {'action':'meeting_read', 'meeting_id':key})
            if item['status'] != 'running': raise ValueError('종료된 회의입니다. 새 안건은 start로 등록하세요.')
            if action == 'speak': return speak(worker, item, args)
            if action != 'finish': raise ValueError('start, speak, finish 중 하나를 사용하세요.')
            summary = str(args.get('summary') or '').strip()
            if not summary: raise ValueError('짧은 결론과 남은 쟁점을 작성하세요.')
            complete = {turn.get('role') for turn in item['minutes'] if turn.get('status') == 'completed' and turn.get('source') == 'hermes_delegate'}
            if len(complete) < 2: raise ValueError('다른 직군도 실제로 검토한 뒤 결론을 내세요.')
            venture = item.get('venture_id') or ''
            if args.get('proposal'):
                proposal = records(worker, {'action':'meeting_proposal', 'meeting_id':key, 'proposal':args['proposal']})
                venture = proposal['venture_id']
            result = records(worker, {'action':'meeting_finish', 'meeting_id':key, 'body':summary, 'venture_id':venture})
            publish(worker, status='completed', role='CEO', text=summary, turn_id='', turn_status='', source_session_id='', venture_id=venture)
            worker.event('meeting_finished', {'id':key, 'venture_id':venture})
            return json.dumps({'meeting_id':key, 'status':result['status'], 'summary':summary, 'venture_id':venture, 'approval':'pending' if venture else None,
                               'instruction':'대표에게 핵심 결론과 승인할 사항만 한국어 두세 문장으로 보고하세요. 발언 전문·기록 ID·상태 코드를 나열하지 마세요.'}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({'error':str(exc)}, ensure_ascii=False)


def speak(worker, item, args):
    from tools.delegate_tool import _build_child_agent, _run_single_child, is_spawn_paused, _get_max_spawn_depth
    if is_spawn_paused(): raise ValueError('Hermes 직원 위임이 일시정지돼 있습니다. 위임을 재개한 뒤 다시 요청하세요.')
    if getattr(worker.agent, '_delegate_depth', 0) >= _get_max_spawn_depth():
        raise ValueError('Hermes의 위임 깊이 한도에 도달했습니다.')
    person = next((role for role in item['roles'] if role['role'] == args.get('role')), None)
    if not person: raise ValueError('start가 반환한 직군 중에서 발언자를 선택하세요.')
    key = item['meeting_id']; turn_id = uuid.uuid4().hex
    focus = str(args.get('focus') or '안건의 핵심 쟁점을 검토하고 앞선 의견의 빈틈이나 개선점을 답하세요.')
    previous = '\n'.join(turn.get('role','')+': '+turn.get('statement','') for turn in item['minutes'] if turn.get('statement'))
    goal = (f"당신은 {person['role']}({person['title']})입니다. 담당 관점: {person['description']}\n"
            f"현재 회의 안건: {item['topic']}\n이번 쟁점: {focus}\n"
            '동료에게 말하듯 쉬운 한국어로 2~3문장만 답하세요. 보고서 목차와 불필요한 외국어를 쓰지 마세요. 앞선 의견을 받아 동의·반론·수정안을 구체적으로 말하세요. '
            '근거가 없으면 불확실성을 밝히고 필요할 때만 웹으로 확인하세요. 회의록/보고서를 쓰거나 다른 역할을 연기하지 마세요. '
            '파일 수정·제품 제작·Git·결제·외부 공개·추가 직원 위임은 하지 마세요.')
    child = _build_child_agent(task_index=len(item['minutes']), goal=goal, context='앞선 실제 발언:\n'+(previous or '아직 없습니다.'),
                               toolsets=['web'], model=None, max_iterations=worker.agent.max_iterations, task_count=1, parent_agent=worker.agent)
    turn = {'id':turn_id, 'role':person['role'], 'name':person['title'], 'statement':'', 'status':'speaking',
            'source':'hermes_delegate', 'source_session_id':child.session_id, 'reply_to':focus, 'created_at':time.time()}
    records(worker, {'action':'meeting_turn', 'meeting_id':key, 'turn':turn})
    publish(worker, role=person['role'], turn_id=turn_id, text='', turn_status='speaking', error='', source_session_id=child.session_id)
    last_write = [time.monotonic()]
    worker.meeting_agent = child
    original_delta = getattr(child, 'stream_delta_callback', None)
    def delta(text, *a, **kw):
        if original_delta: original_delta(text, *a, **kw)
        if not isinstance(text, str): return
        turn['statement'] += text
        publish(worker, text=turn['statement'])
        if time.monotonic()-last_write[0] >= 1:
            records(worker, {'action':'meeting_turn', 'meeting_id':key, 'turn':dict(turn)})
            last_write[0] = time.monotonic()
    child.stream_delta_callback = delta
    try:
        result = _run_single_child(task_index=len(item['minutes']), goal=goal, child=child, parent_agent=worker.agent)
        if result.get('status') in ('error','failed','timeout','interrupted','cancelled') or worker.stopping:
            raise RuntimeError(result.get('error') or result.get('summary') or '발언이 중단됐습니다.')
        final = str(result.get('summary') or turn['statement']).strip()
        if not final: raise RuntimeError('직원의 응답이 비어 있습니다.')
        turn.update(statement=final, status='completed')
        records(worker, {'action':'meeting_turn', 'meeting_id':key, 'turn':turn})
        publish(worker, text=final, turn_status='completed')
        return json.dumps({'meeting_id':key, 'role':person['role'], 'statement':final, 'source_session_id':child.session_id,
                           'instruction':'Choose the next role or ask a previous role to respond to this statement. Finish when the issue is resolved; do not force every role to speak.'}, ensure_ascii=False)
    except Exception as exc:
        publish(worker, turn_status='failed', error=str(exc))
        turn.update(status='failed', error=str(exc))
        records(worker, {'action':'meeting_turn', 'meeting_id':key, 'turn':turn})
        raise
    finally:
        with worker.lock:
            usage = worker.job.setdefault('meeting_usage', {})
            for key, attr in [('input_tokens','session_input_tokens'),('output_tokens','session_output_tokens'),('api_calls','session_api_calls')]:
                usage[key] = usage.get(key,0) + int(getattr(child,attr,0) or 0)
            worker.meeting_agent = None


def settle(worker, completion):
    item = worker.job.get('meeting') or {}
    if not item.get('id') or item.get('status') != 'running': return
    reason = completion.get('error') or '총괄 실행이 종료됐지만 회의 결론이 기록되지 않았습니다.'
    try:
        records(worker, {'action':'meeting_finish', 'meeting_id':item['id'], 'status':'failed', 'body':reason})
        publish(worker, status='failed', error=reason)
        if completion.get('state') == 'complete': completion.update(state='paused', error=reason)
    except Exception as exc:
        completion['error'] = reason+' 회의 상태 기록 실패: '+str(exc)


def owner_message(worker, message, turn_id=None):
    item = worker.job.get('meeting') or {}
    if not message or not item.get('id') or item.get('status') != 'running': return
    try:
        records(worker, {'action':'meeting_turn', 'meeting_id':item['id'], 'turn':{
            'id':turn_id or uuid.uuid4().hex, 'role':'OWNER', 'name':'대표', 'statement':message,
            'status':'completed', 'source':'owner', 'source_session_id':worker.job['session_id'], 'created_at':time.time()}})
    except Exception as exc:
        worker.event('meeting_record_error', {'error':str(exc)})
