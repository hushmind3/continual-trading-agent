"""Company records as native Hermes tools; no second agent or conversation store."""
import json
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
    if not worker.company_link:
        return ''
    # start_chat already validates an explicit directory. Keep that selection;
    # the organization's root is only the default, not a forced replacement.
    cfg['workspace'] = str(Path(workspace).expanduser().resolve()) if workspace else worker.company_link['workspace']
    return ('\nYou are the company CEO in this persistent native Hermes session. '
            'Use company_records for company facts, proposals, role assignments and evidence-backed results. '
            'Your native history, memory, tools and Goal/Loop are active; there is no separate execution model. '
            'Old imported claims about unavailable tools or disconnected models are historical, not current facts. '
            'The organization may be a company, team or any owner-defined group. Discuss naturally. '
            'An explicit owner instruction to create something authorizes that task; begin can omit venture_id. '
            'For a new business initiative you propose yourself, submit a concrete proposal for owner approval first. '
            'Choose roles and task order to fit the goal; do not require CPO→CTO→QA for every request. '
            'Use native file/terminal tools or native delegation to deliver working results, then record evidence. '
            'Do not stop at review documents when the owner requested a functioning website or program. '
            'Keep detailed deliberations in meeting records and report concise decisions to the owner. '
            'Proceed autonomously within owner instructions. Ask through native clarify/approval only when '
            'credentials, account authentication, spending approval or missing owner information actually blocks progress; '
            'resume the same task after the answer. Payments such as PayPal require actual account authorization; '
            'do not claim a payment connection or revenue from a plan alone. '
            'Do not claim tests, builds, publication, customers or revenue without evidence. '
            'The company tool records work; it never launches another agent. External publishing still requires owner authorization. '
            'Use only the current owner instruction for new actions; historical owner requests are context. '
            'On this Windows host terminal uses Git Bash. node and npm are already on PATH: use node/npm directly. '
            'Do not use unquoted Program Files paths, do not invent a Temp workspace, and do not install tools globally. '
            'Use company_records begin workspace for project operations and write_file/patch for code in small files. '
            'For npm versions, package_info, install, test and build use project_npm with that exact workspace. '
            'This executes directly without shell/cd/path quoting; do not run npm in Temp or globally.')


def execute(args, **kwargs):
    worker = _worker
    link = getattr(worker, 'company_link', None)
    if not link:
        return json.dumps({'error': '이 세션에 연결된 회사가 없습니다.'}, ensure_ascii=False)
    if getattr(worker.agent, '_read_only_denials', None) is not None and args.get('action', 'overview') != 'overview':
        return json.dumps({'error': '읽기 모드에서는 회사 기록을 변경할 수 없습니다.'}, ensure_ascii=False)
    command = dict(args)
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
        with urlopen(Request(link['url'], data=body, headers={'Content-Type': 'application/json'}), timeout=60) as response:
            result = json.load(response)
        return json.dumps(result, ensure_ascii=False)
    except HTTPError as exc:
        # Keep actionable validation errors (e.g. unknown job id), rather than
        # reducing every rejected command to an opaque "400 Bad Request".
        detail = exc.read(12000).decode('utf-8', errors='replace').replace(link['token'], '[redacted]')
        return json.dumps({'error': f'회사 기록 요청 실패 (HTTP {exc.code})', 'detail': detail}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({'error': str(exc)}, ensure_ascii=False)


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


SCHEMA = {'name': 'company_records', 'description': 'Company facts and records, not a separate AI engine. overview reads status; propose submits a business for owner approval; begin records a role assignment and returns the REAL job_id/workspace. Use that returned job_id. finish records SUCCESS with evidence in body; fail records an ACTUAL FAILURE with reason in body. There is no error argument. meeting saves minutes and a concise summary. Roles: CPO product/design, CTO implementation, CMO marketing, CFO finance, CS customers, QA verification. You choose roles/order.',
    'parameters': {'type': 'object', 'properties': {
        'action': {'type': 'string', 'enum': ['overview', 'propose', 'begin', 'finish', 'fail', 'meeting']},
        'venture_id': {'type': 'string'}, 'job_id': {'type': 'string'},
        'role': {'type': 'string', 'enum': ['CEO', 'CPO', 'CTO', 'CMO', 'CFO', 'CS', 'QA']},
        'title': {'type': 'string'}, 'body': {'type': 'string', 'description': 'Actual success evidence for finish; actual failure reason for fail. Success must never be recorded as an error.'},
        'proposal': {'type': 'object'}, 'minutes': {'type': 'array', 'items': {'type': 'object'}}},
        'required': ['action'], 'additionalProperties': False}}


def register():
    from tools.registry import registry
    from toolsets import TOOLSETS, _resolve_toolset_memo
    registry.register(name='company_records', toolset='platform_company', schema=SCHEMA, handler=execute)
    from ai_agent.Hermes.chat.project_commands import SCHEMA as NPM_SCHEMA, run
    registry.register(name='project_npm', toolset='platform_company', schema=NPM_SCHEMA, handler=lambda args,**kw:run(_worker,args))
    TOOLSETS['platform_company'] = {'description': 'Connected company records', 'tools': ['company_records','project_npm']}
    _resolve_toolset_memo.clear()
