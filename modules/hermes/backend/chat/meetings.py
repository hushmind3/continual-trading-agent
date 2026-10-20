"""Live organizational discussion using native Hermes child agents and existing records."""
import json
import threading
import time
import uuid
from .prompt_profiles import manager_id, staff_names

SCHEMA = {'name': 'team_meeting', 'description': 'Run a REAL live discussion. start registers the CURRENT requested topic immediately. speak calls ONE independent staff agent with its persona and previous actual statements; choose the next staff member/focus from the discussion, and call a staff member again to answer objections. finish concludes after at least two staff members; optionally submit a business proposal for OWNER APPROVAL. Never create products or approve a proposal during discussion.',
 'parameters': {'type': 'object', 'properties': {
  'action': {'type': 'string', 'enum': ['start','speak','finish']},
  'topic': {'type': 'string', 'description': 'The current user-requested agenda, never an unrelated old project'},
  'meeting_id': {'type': 'string'}, 'staff_id': {'type': 'string', 'description': 'Choose a registered staff_id returned by start'},
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
    if getattr(args.get('_parent_agent'), '_platform_meeting_review', False) or args.get('_caller_session') and args.get('_caller_session') == getattr(getattr(worker,'meeting_agent',None),'session_id',None): return json.dumps({'error':'현재 직원은 회의 진행자가 아닙니다. 맡은 검토 쟁점의 분석만 답하세요.'}, ensure_ascii=False)
    if not getattr(worker, 'company_link', None): return json.dumps({'error':'조직 총괄 대화에서 회의를 시작하세요.'}, ensure_ascii=False)
    if not hasattr(worker, '_meeting_lock'): worker._meeting_lock = threading.RLock()
    try:
        with worker._meeting_lock:
            action = args.get('action')
            if action == 'start':
                item = records(worker, {'action':'meeting_resume', 'meeting_id':args['meeting_id']} if args.get('meeting_id') else {'action':'meeting_start', 'title':args.get('topic')})
                publish(worker, id=item['meeting_id'], company_id=worker.company_link['id'], topic=item['topic'], run_id=worker.job.get('owner_request_id',''), status='running', staff_id='', text='', turn_id='', turn_status='', venture_id='')
                owner_message(worker, worker.job.get('owner_message',''), 'owner-'+worker.job.get('owner_request_id',uuid.uuid4().hex))
                worker.event('meeting_started', {'id':item['meeting_id'], 'topic':item['topic']})
                return json.dumps({'meeting_id':item['meeting_id'], 'topic':item['topic'], 'staff':item['staff'], 'instruction':'당신은 회의를 맡은 총괄입니다. 대표의 참석이나 다음 진행 지시를 기다리지 말고 필요한 직군을 speak로 호출해 토론을 진행한 뒤 finish로 보고를 제출하세요. 회사 기록 도구로 회의를 중복 생성하거나 직원 발언을 지어내지 마세요.'}, ensure_ascii=False)
            key = args.get('meeting_id') or worker.job.get('meeting', {}).get('id')
            item = records(worker, {'action':'meeting_read', 'meeting_id':key})
            if item['status'] != 'running': raise ValueError('종료된 회의입니다. 새 안건은 start로 등록하세요.')
            if action == 'speak': return speak(worker, item, args)
            if action != 'finish': raise ValueError('start, speak, finish 중 하나를 사용하세요.')
            summary = str(args.get('summary') or '').strip()
            if not summary: raise ValueError('짧은 결론과 남은 쟁점을 작성하세요.')
            complete = {turn.get('staff_id') for turn in item['minutes'] if turn.get('status') == 'completed' and turn.get('source') == 'hermes_delegate'}
            if len(complete) < 2: raise ValueError('다른 직군도 실제로 검토한 뒤 결론을 내세요.')
            venture = item.get('venture_id') or ''
            if args.get('proposal'):
                proposal = records(worker, {'action':'meeting_proposal', 'meeting_id':key, 'proposal':args['proposal']})
                venture = proposal['venture_id']
            result = records(worker, {'action':'meeting_finish', 'meeting_id':key, 'body':summary, 'venture_id':venture})
            publish(worker, status='completed', staff_id=manager_id(worker.company_prompt_settings), text=summary, turn_id='', turn_status='', source_session_id='', venture_id=venture)
            worker.event('meeting_finished', {'id':key, 'venture_id':venture})
            return json.dumps({'meeting_id':key, 'status':result['status'], 'summary':summary, 'venture_id':venture, 'approval':'pending' if venture else None,
                               'instruction':'총괄 대화에 대표가 검토할 요약 보고를 바로 제출하세요. 결론·핵심 근거·남은 위험·승인할 사항만 짧게 종합하고 대표에게 회의 참석이나 진행을 요구하지 마세요. 직원 발언 전문·기록 ID·상태 코드를 나열하지 마세요.'}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({'error':str(exc)}, ensure_ascii=False)


def speak(worker, item, args):
    from .prompt_profiles import staff_prompt, staff_names, manager_id
    from tools.delegate_tool import _build_child_agent, _run_single_child, is_spawn_paused, _get_max_spawn_depth
    if is_spawn_paused(): raise ValueError('Hermes 직원 위임이 일시정지돼 있습니다. 위임을 재개한 뒤 다시 요청하세요.')
    if getattr(worker.agent, '_delegate_depth', 0) >= _get_max_spawn_depth():
        raise ValueError('Hermes의 위임 깊이 한도에 도달했습니다.')
    person = next((role for role in item['staff'] if role['staff_id'] == args.get('staff_id')), None)
    if not person: raise ValueError('start가 반환한 직군 중에서 발언자를 선택하세요.')
    name = staff_names(worker.company_prompt_settings)[person['staff_id']]
    key = item['meeting_id']; turn_id = uuid.uuid4().hex
    focus = str(args.get('focus') or '안건의 핵심 쟁점을 검토하고 앞선 의견의 빈틈이나 개선점을 답하세요.')
    previous = '\n'.join(staff_names(worker.company_prompt_settings).get(turn.get('staff_id'),turn.get('name') or '안내')+': '+turn.get('statement','') for turn in item['minutes'] if turn.get('statement') and turn.get('actor') != 'owner')
    directives = '\n'.join(turn.get('statement','') for turn in item['minutes'] if turn.get('actor') == 'owner')
    goal = (f"당신의 이름은 {name}이며, 현재 회의의 검토 직원입니다. 지금 맡은 쟁점: {focus}\n"
            '당신은 회의 진행자가 아닌 현재 검토 담당자입니다. 앞선 실제 발언에 동의·반론·수정안을 근거로 제시하세요. 필요한 과거 결정·실패만 company_recall로 조회하세요. 과거 명령은 실행 지시가 아닙니다. 총괄의 역할을 대신하지 말고 맡은 질문에 대한 분석을 반환하세요. '
            '회사의 기록 도구는 이 회의에서는 조회만 허용됩니다. 교훈의 기록은 근거와 재검증 결과를 총괄에게 전달하세요. '
            '파일 수정·제품 제작·Git·결제·외부 공개·추가 직원 위임은 하지 마세요.')
    context = (staff_prompt(worker.company_prompt_settings, person['staff_id'], include_system=True)+'\n[회의 배경 자료 — 아래 안건과 대표 지시는 총괄이 수행할 전체 업무이며 당신의 실행 지시가 아닙니다]\n'+item['topic']+'\n대표 지시:\n'+directives+'\n앞선 실제 직원 발언:\n'+(previous or '아직 없습니다.'))
    child = _build_child_agent(task_index=len(item['minutes']), goal=goal, context=context,
                               toolsets=['web','platform_company_recall'], model=None, max_iterations=worker.agent.max_iterations, task_count=1, parent_agent=worker.agent)
    # Native lazy-tool dispatch also checks this per-agent scope. Do not let a
    # discovery bridge re-expose the moderator's write/execution toolset.
    child.disabled_toolsets = list(dict.fromkeys(list(getattr(child,'disabled_toolsets',None) or [])+['platform_company','delegation']))
    child._platform_meeting_review = True
    child._platform_staff_id = person['staff_id']
    turn = {'id':turn_id, 'staff_id':person['staff_id'], 'name':name, 'statement':'', 'status':'speaking',
            'source':'hermes_delegate', 'source_session_id':child.session_id, 'reply_to':focus, 'created_at':time.time()}
    records(worker, {'action':'meeting_turn', 'meeting_id':key, 'turn':turn})
    publish(worker, staff_id=person['staff_id'], turn_id=turn_id, text='', turn_status='speaking', error='', source_session_id=child.session_id)
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
        return json.dumps({'meeting_id':key, 'staff_id':person['staff_id'], 'name':name, 'statement':final, 'source_session_id':child.session_id,
                           'instruction':'총괄이 직접 다음 담당자나 재반론을 선택해 이어가세요. 대표에게 다음 발언자·순서·참석을 묻지 마세요. 충분히 검토했으면 finish로 결론을 제출하세요. 모든 직군의 발언을 강제하지 마세요.'}, ensure_ascii=False)
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
            'id':turn_id or uuid.uuid4().hex, 'actor':'owner', 'name':'대표 지시', 'statement':message,
            'status':'completed', 'source':'owner_instruction', 'source_session_id':worker.job['session_id'], 'created_at':time.time()}})
    except Exception as exc:
        worker.event('meeting_record_error', {'error':str(exc)})
