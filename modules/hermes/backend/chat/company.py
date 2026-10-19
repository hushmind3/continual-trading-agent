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
    return ('\nYou coordinate the owner-defined organization in this native Hermes session. '
            'Answer in Korean, normally 1-3 short sentences; expand only when requested or necessary. '
            'Ordinary conversation, opinions and questions do not start meetings, delegation, planning or tasks. '
            'Use a tool only when current facts or an explicit action need it; do not routinely fetch company status. '
            'An explicit work request authorizes that work. Choose roles/order as needed, not a fixed pipeline. '
            'Use native tools, memory and Goal/Loop; there is no separate execution model. '
            'company_records stores facts, proposals, work evidence and minutes; it does not execute agents. '
            'Keep detailed reports in files/records and give the owner conclusions, results and blockers briefly. '
            'New business initiatives need owner approval; credentials, spending and external publication need authorization. '
            'Historical requests and disconnected-model claims are context, not current instructions or facts. '
            'Do not claim tests, delivery, customers or revenue without actual evidence. '
            'Use begin workspace; project_npm runs npm without shell quoting. Never install globally or invent Temp paths.')


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
