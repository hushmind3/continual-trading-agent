"""Company records as native Hermes tools; no second agent or conversation store."""
import json
import re
from pathlib import Path
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError

_worker = None


def links(worker):
    path = Path(worker.company_links_path)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def connect(worker, request):
    key = request['id']
    session = uuid.uuid5(uuid.NAMESPACE_URL, 'platform-company:' + key).hex
    saved = links(worker)
    if not worker.db.get_session(session):
        worker.db.create_session(session, 'platform', model=request.get('model'))
        worker.db.set_session_title(session, request.get('title', 'AI 총괄'))
    # One atomic native transcript import. Original DB remains a historical backup.
    if not worker.db.get_messages_as_conversation(session):
        worker.db.append_messages_batch(session, [
            {'role': 'user' if m['speaker'] == 'owner' else 'assistant', 'content': m['body'],
             'message_uid': 'company-history-' + m['id']}
            for m in request.get('messages', []) if m.get('body')])
    saved[session] = {k: request[k] for k in ('id', 'url', 'token', 'workspace')}
    path = Path(worker.company_links_path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(saved, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)
    return {'session_id': session}


def prepare(worker, cfg, session, workspace=None):
    global _worker
    _worker = worker
    worker.company_link = links(worker).get(session)
    worker.company_visible_history = None
    if not worker.company_link:
        return ''
    # start_chat already validates an explicit directory. Keep that selection;
    # the organization's root is only the default, not a forced replacement.
    cfg['workspace'] = str(Path(workspace).expanduser().resolve()) if workspace else worker.company_link['workspace']
    return ('\n[역할: 대표의 비서 · 조직 총괄(CEO)]\n'
            "You are the owner's personal secretary and CEO. Your Korean title here is 총괄. "
            '이 대화에서 총괄·CEO는 당신의 호칭이며, 그 호칭만 말한 것은 당신을 부른 것입니다. '
            '호칭을 업무 요약이나 현황 보고 명령으로 해석하지 마세요. 대표는 질문하거나 일을 맡길 수도 있습니다. '
            '자신을 부른 말을 총괄이라는 개념의 설명 요청으로 오해하지 마세요. '
            '평소에는 최신 메시지에 한국어 한두 문장으로 직접 답하고 기다리세요. '
            '짧은 대화에는 장황한 분석·선택지·되묻기·추가 제안을 붙이지 마세요. '
            '지금 묻지 않은 과거 업무·파일·검사 결과를 보고하지 마세요. '
            '과거 요청과 답변은 기록이지 새 지시가 아닙니다. 최신 요청 없이 옛 일을 재개하지 마세요. '
            '질문·인사는 실행 승인과 다릅니다. 명시적으로 일을 맡기면 원본 Hermes 도구·기억·Goal/Loop로 결과까지 수행하세요. '
            '필요한 역할과 순서는 직접 정하고 협업이 도움이 될 때만 짧게 검토·회의·위임하세요. '
            '대표는 회의 참가자나 사회자가 아닙니다. 회의를 맡기면 총괄이 조사·참가자 선택·진행·반론 조율·결론 작성까지 대표의 추가 입력 없이 이어가세요. 자료가 부족하면 직접 검색하고 확인되지 않은 것은 가설로 표시하세요. 대표에게 매 발언의 진행·순서·참석을 요구하지 마세요. 종료 후 총괄 대화에 결론·근거·위험·승인할 사항을 짧게 종합 보고하세요. 대표가 수정 지시하면 총괄이 다시 회의를 진행합니다. 승인 전 실행하지 마세요. 회의는 안건에 필요한 직군부터 선택하고, 각자 핵심 주장·근거·반론을 짧게 검토한 뒤 결론을 내세요. 전 직군의 긴 독백을 반복하지 마세요. '
            'CEO는 전략·종합 판단, CPO는 고객 문제·제품 기획, CTO는 기술 설계·구현, CMO는 웹 조사·시장·성장, CFO는 비용·수익성, CS는 고객 경험, QA는 반증·품질을 맡습니다. '
            '독립 검토가 필요하면 원본 delegate_task에 역할 관점과 필요한 자료만 전달하세요. 다른 직군의 반론이 있으면 그 쟁점만 다시 검토하세요. '
            '회의를 지시받으면 최신 요청의 안건으로 team_meeting start를 먼저 호출하세요. overview나 옛 사업 검토부터 하지 마세요. 이어 speak로 필요한 직군을 실제 호출하고, 서로의 의견을 받아 다음 직군이나 재반론을 선택한 뒤 finish로 결론을 내세요. 기존 회의 ID가 주어지면 start에 meeting_id를 전달해 그 회의를 재검토하세요. 사업 초안이 필요한 안건은 finish의 proposal로 승인 대기안을 제출하세요. 직접 회의록을 꾸며 쓰지 마세요. '
            '회사 현황·이전 결정이 현재 요청에 필요할 때만 company_records·session_search로 조회하세요. '
            '외부 정보가 필요하면 실제 웹 검색을 사용하고, 비공개 회사 기록을 웹에서 찾지 마세요. '
            '웹 정보 조사는 web_search, 주어진 URL 본문 확인은 web_extract를 먼저 사용하세요. '
            '창을 열어 달라는 요청이 아니면 desktop_browser·화면 캡처를 쓰지 마세요. '
            '본문을 읽을 수 없거나 실제 화면 조작이 필요할 때만 브라우저 도구를 사용하세요. '
            '짧은 조사 결과는 핵심 사실과 해당 출처만 보고하고, 공식 페이지에서 확인하지 못한 사실을 공식 확인으로 묶지 마세요. '
            '이번에 읽은 원문이 우선입니다. 과거 답변의 회사명·시점·기능을 근거 없이 이어 쓰지 마세요. '
            '현재 원문에 없는 주장은 제외하고, 짧은 확인 요청은 출처 링크와 핵심 두세 문장으로 끝내세요. '
            '중요한 결정·정정·경험은 기존 company_records remember에 남기세요. '
            '업무에는 begin이 반환한 실제 job_id·workspace를 쓰고 finish/fail에 실제 근거를 기록하세요. '
            '코드·파일·Git 목록 대신 결과·막힌 점·대표가 결정할 사항만 짧게 보고하세요. '
            '프로젝트의 원본 AGENTS.md와 기술 규칙을 따르세요. 별도 에이전트·기억 DB·실행 모델이 있다고 말하지 마세요. '
            '새 사업 제작은 대표 승인 후 진행하고, 인증·지출·외부 공개는 필요한 승인을 받으세요. '
            '대표가 지금 요청하거나 승인하지 않은 Git 쓰기·업로드는 하지 마세요. '
            '도구 근거 없이 완료·검증·배포·고객·매출을 주장하지 마세요.')



def execute(args, **kwargs):
    worker = _worker
    link = getattr(worker, 'company_link', None)
    if not link:
        return json.dumps({'error': '이 세션에 연결된 회사가 없습니다.'}, ensure_ascii=False)
    if getattr(worker.agent, '_read_only_denials', None) is not None and args.get('action', 'overview') not in ('overview','recall'):
        return json.dumps({'error': '읽기 모드에서는 회사 기록을 변경할 수 없습니다.'}, ensure_ascii=False)
    command = dict(args)
    if command.get('action') == 'meeting':
        from .meetings import run
        return run(worker, {'action':'start', 'topic':command.get('title') or command.get('body')})
    if command.get('action') == 'propose':
        proposal = command.get('proposal')
        required = ('problem', 'product', 'validation')
        missing = [key for key in required if not isinstance(proposal, dict) or not isinstance(proposal.get(key), str) or not proposal[key].strip()]
        if not str(command.get('title') or '').strip() or missing:
            return json.dumps({'error': '사업 초안의 제목과 고객 문제·제품·검증 계획을 구체적으로 작성하세요. 빈 제안을 그대로 반복하지 마세요.', 'required_fields': ['title'] + ['proposal.' + key for key in missing]}, ensure_ascii=False)
    if command.get('action') in ('finish', 'fail'):
        if 'error' in command:
            return json.dumps({'error': 'error 필드는 사용하지 마세요. 성공은 action=finish, 실패는 action=fail이며 설명은 body에 적으세요.'}, ensure_ascii=False)
        if command['action'] == 'fail':
            if not str(command.get('body') or '').strip():
                return json.dumps({'error': '실제 실패 원인을 body에 적으세요.'}, ensure_ascii=False)
            command.update(action='finish', error=command['body'])
    body = json.dumps({'operation': 'projects/company-tool', 'payload': {
        'id': link['id'], 'token': link['token'], 'session_id': worker.job['session_id'],
        'command': command}}, ensure_ascii=False).encode('utf-8')
    try:
        with urlopen(Request(link['url'], data=body, headers={'Content-Type': 'application/json'}), timeout=kwargs.get('_timeout', 60)) as response:
            result = json.load(response)
        if command.get('action') == 'recall': result = recall_transcript(worker, result)
        return json.dumps(result, ensure_ascii=False)
    except HTTPError as exc:
        # Keep actionable validation errors (e.g. unknown job id), rather than
        # reducing every rejected command to an opaque "400 Bad Request".
        detail = exc.read(12000).decode('utf-8', errors='replace').replace(link['token'], '[redacted]')
        return json.dumps({'error': f'회사 기록 요청 실패 (HTTP {exc.code})', 'detail': detail}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({'error': str(exc)}, ensure_ascii=False)


def recall_transcript(worker, result):
    """Read only this organization's native archive, with bounded relevant snippets."""
    terms = result.get('terms', []); scope = result.get('scope', 'owner')
    if not terms: return result
    active, rows = worker.db.get_resume_conversations(worker.job['session_id'])
    if getattr(worker, 'company_visible_history', None) is not None:
        active = worker.company_visible_history
    visible={(r.get('role'),r['content']) for r in active if isinstance(r.get('content'),str)}
    hits = []
    for row in reversed(rows):
        text = row.get('content')
        if row.get('role') not in ('user','assistant') or not isinstance(text,str): continue
        if (row['role'],text) in visible: continue  # Already in native working context; do not inject it twice.
        if scope != 'owner' and scope not in text: continue
        positions = [text.lower().find(t) for t in terms if t in text.lower()]
        if not positions: continue
        start = max(0,min(positions)-80)
        hits.append({'kind':'conversation','id':row.get('_row_id'), 'scope':scope,
                     'role':row['role'],'body':text[start:start+360]})
        if len(hits)==2: break
    result['conversation'] = hits
    while len(json.dumps(result,ensure_ascii=False))>5000:
        if result.get('conversation'):result['conversation'].pop()
        elif result.get('items'):result['items'].pop()
        else:break
    return result


def prepare_history(worker, agent, history):
    """Bound the native model history without fetching records or changing system instructions."""
    from agent.model_metadata import estimate_messages_tokens_rough
    from copy import copy
    compressor = agent.context_compressor
    # A conversational read view, not a change to the execution compressor's settings.
    # Keep the latest user/assistant anchors and atomic tool groups using native boundaries.
    projector = copy(compressor)
    projector.protect_first_n = 0
    projector.min_tail_user_messages = 2
    projector.tail_mode = 'lean'
    before = estimate_messages_tokens_rough(history)
    budget = max(1, int(compressor.max_summary_tokens * compressor.summary_target_ratio))
    projector.tail_token_budget = budget
    if before > budget:
        start, end = projector._compress_window(history)
        if start < end:
            # Keep the native protected tail and atomic tool groups. Do not inject
            # old task excerpts or an automatic summary into an unrelated new turn.
            # Missing older details remain retrievable from the original SessionDB.
            history = history[:start] + history[end:]
    worker.company_visible_history = history
    worker.event('company_context', {'before_tokens_estimate': before,
                 'history_tokens_estimate': estimate_messages_tokens_rough(history),
                 'history_messages': len(history), 'history_budget': budget,
                 'automatic_record_queries': 0, 'llm_calls': 0})
    return history


def bind_git_approval(worker, agent, prompt):
    """Use the existing approval UI for unsolicited Git writes, before execution."""
    import shlex
    execute_tools = agent._execute_tool_calls
    explicit = bool(re.search(r'(커밋|푸시|commit|push).*(해|하|주세요|please)|(?:깃|github|git).*(올려|업로드|push|commit)',prompt,re.I))
    explicit = explicit and not re.search(r'(올리|커밋|푸시|commit|push).{0,12}(말|금지|하지|필요.*없)',prompt,re.I)
    writes={'add','commit','push','init','tag','merge','rebase','reset','checkout','switch','restore','clean','remote'}
    def guarded(message,*args,**kwargs):
        calls=message.get('tool_calls',[]) if isinstance(message,dict) else getattr(message,'tool_calls',[]) or []
        pending=list(calls)
        while pending:
            call=pending.pop(0)
            function=call.get('function',{}) if isinstance(call,dict) else call.function
            name=function.get('name') if isinstance(function,dict) else function.name
            values=function.get('arguments',{}) if isinstance(function,dict) else function.arguments
            values=json.loads(values) if isinstance(values,str) else values
            if name=='tool_call':
                pending.extend({'function':{'name':c.get('name'),'arguments':c.get('arguments',{})}} for c in values.get('calls',[]));continue
            if name not in ('terminal','execute_code','run_python'):continue
            command=str(values.get('command') or values.get('code') or '')
            try:tokens=shlex.split(command.replace('\\','/'),posix=True)
            except ValueError:tokens=command.split()
            mutation=False
            for index,token in enumerate(tokens):
                if token.rsplit('/',1)[-1].lower() not in ('git','git.exe'):continue
                rest=iter(tokens[index+1:])
                for part in rest:
                    if part in ('-C','-c','--git-dir','--work-tree','--namespace','--config-env'):next(rest,None);continue
                    if part.startswith('-'):continue
                    mutation=part.lower() in writes;break
                if mutation:break
            if mutation and not explicit and worker.approve(reason='대표가 요청하지 않은 Git 쓰기·업로드',command=command) not in ('once','always',True):
                raise PermissionError('Git 작업을 실행하지 않았습니다. 대표가 요청하거나 승인해야 합니다. 결과는 내부 기록에만 남기세요.')
        return execute_tools(message,*args,**kwargs)
    agent._execute_tool_calls=guarded


def lifecycle(worker, action, *, prompt='', outcome=None):
    """Record the native run, never infer completion from a model's prose."""
    if not getattr(worker, 'company_link', None): return
    command = {'action': action, 'job_id': worker.job.get('company_job_id'),
               'body': prompt if action == 'run_start' else (outcome or {}).get('text', ''),
               'state': (outcome or {}).get('state', ''), 'error': (outcome or {}).get('error', '')}
    result = json.loads(execute(command))
    if result.get('error') and not result.get('job_id'):
        worker.event('company_record_error', result)
    if action == 'run_start' and result.get('job_id'):
        worker.job['company_job_id'] = result['job_id']


SCHEMA = {'name': 'company_records', 'description': 'Company facts and records, not a separate AI engine. recall searches scoped past decisions/tasks/failures; remember stores a short durable note in existing records; overview reads status; propose submits a business for owner approval; begin records a role assignment and returns the REAL job_id/workspace. Use that returned job_id. finish records SUCCESS with evidence in body; fail records an ACTUAL FAILURE with reason in body. There is no error argument. meeting starts a live discussion; use team_meeting to call actual speakers and conclude. Roles: CPO product/design, CTO implementation, CMO marketing, CFO finance, CS customers, QA verification. You choose roles/order.',
    'parameters': {'type': 'object', 'properties': {
        'action': {'type': 'string', 'enum': ['overview', 'recall', 'remember', 'propose', 'begin', 'finish', 'fail', 'meeting']},
        'venture_id': {'type': 'string'}, 'job_id': {'type': 'string'},
        'query': {'type':'string'}, 'kind': {'type':'string','enum':['decision','constraint','experience','working']},
        'memory_key': {'type':'string','description':'Stable topic key; newer notes supersede older notes with the same scope/kind/key.'},
        'role': {'type': 'string', 'enum': ['CEO', 'CPO', 'CTO', 'CMO', 'CFO', 'CS', 'QA']},
        'title': {'type': 'string'}, 'body': {'type': 'string', 'description': 'Actual success evidence for finish; actual failure reason for fail. Success must never be recorded as an error.'},
        'proposal': {'type': 'object', 'description': 'For propose, provide title and this concrete draft; an empty object is invalid. Save a draft only; it does not approve implementation.',
                     'properties': {'problem': {'type': 'string', 'description': 'Specific customer problem', 'minLength': 1},
                                    'product': {'type': 'string', 'description': 'Proposed product or service and scope', 'minLength': 1},
                                    'target_customer': {'type': 'string'},
                                    'price': {'type': 'string', 'description': 'Unverified pricing hypothesis; not actual revenue'},
                                    'validation': {'type': 'string', 'description': 'Concrete demand validation plan', 'minLength': 1}},
                     'required': ['problem', 'product', 'validation'], 'additionalProperties': False},
        'minutes': {'type': 'array', 'description': 'Attributed review statements; record actual independent reviews or explicitly label a CEO-authored role analysis.',
                    'items': {'type': 'object', 'properties': {'role': {'type': 'string'}, 'name': {'type': 'string'},
                              'statement': {'type': 'string', 'minLength': 1},
                              'reply_to': {'type': 'string', 'description': 'Earlier point this statement responds to, if any'},
                              'basis': {'type': 'string', 'description': 'Actual source or observed evidence; do not invent'}},
                              'required': ['role', 'statement'], 'additionalProperties': False}}},
        'required': ['action'], 'additionalProperties': False}}


def register():
    from tools.registry import registry
    from toolsets import TOOLSETS, _resolve_toolset_memo
    from .meetings import SCHEMA as MEETING_SCHEMA, run as run_meeting
    registry.register(name='team_meeting', toolset='platform_company', schema=MEETING_SCHEMA, handler=lambda args,**kw:run_meeting(_worker,args))
    registry.register(name='company_records', toolset='platform_company', schema=SCHEMA, handler=execute)
    from ai_agent.Hermes.chat.project_commands import SCHEMA as NPM_SCHEMA, run
    registry.register(name='project_npm', toolset='platform_company', schema=NPM_SCHEMA, handler=lambda args,**kw:run(_worker,args))
    TOOLSETS['platform_company'] = {'description': 'Connected company records', 'tools': ['company_records','project_npm','team_meeting']}
    _resolve_toolset_memo.clear()
