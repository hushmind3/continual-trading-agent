"""Original company conversation API through the existing platform router."""
import base64
import json
import re
import secrets
import uuid
from urllib.parse import urlsplit
from . import runtime, store


def call(key, payload, origin=None):
    record = store.read(key)
    if record.get('stage') != 'ready' or record.get('workspace_ui', {}).get('recipe') != 'company-v1' or not record.get('harness', {}).get('enabled'):
        raise ValueError('연결된 AI 총괄 대화가 없습니다.')

    def invoke(path, method='GET', body=None, token=None):
        value = {'path': path, 'method': method, 'headers': {'X-Project-Zero-Token': token} if token else {}}
        if body is not None:
            value['body'] = json.dumps(body, ensure_ascii=False)
            value['headers']['Content-Type'] = 'application/json'
        response = runtime.invoke(record, value, origin)
        result = json.loads(base64.b64decode(response['body']))
        if response['status'] >= 400: raise ValueError(result.get('detail', '앱 대화 요청에 실패했습니다.'))
        return result

    token = invoke('/api/local/session')['token']
    action = payload.get('action', 'state')
    native_id = uuid.uuid5(uuid.NAMESPACE_URL, 'platform-company:' + key).hex
    if action == 'session':
        from ai_agent.Hermes.engine.bridge import bridge
        with store.LOCK:
            record = store.read(key)
            native = record.setdefault('workspace_ui', {}).setdefault('native', {})
            native.setdefault('token', secrets.token_urlsafe(32))
            store.save(record)
        workspace = store.project_folder(record) / 'workspaces'
        workspace.mkdir(parents=True, exist_ok=True)
        root = str(origin.base_url) if origin is not None else 'http://127.0.0.1:8766/'
        parsed = urlsplit(root)
        if parsed.hostname not in ('127.0.0.1', 'localhost', '::1'): raise ValueError('로컬 플랫폼 연결만 사용할 수 있습니다.')
        history = invoke('/api/admin/ceo', token=token)
        return bridge.call('company/session', {'id': key, 'title': 'AI 총괄 · ' + record.get('name', key),
            'workspace': str(workspace), 'url': root.rstrip('/') + '/api', 'token': native['token'],
            'messages': history['messages']})
    if action == 'tool':
        native = record.get('workspace_ui', {}).get('native', {})
        session_id = payload.get('session_id')
        if not native.get('token') or not secrets.compare_digest(str(payload.get('token', '')), native['token']):
            raise ValueError('회사 도구의 네이티브 세션 인증에 실패했습니다.')
        if session_id != native_id:
            if not isinstance(session_id,str) or not re.fullmatch('[A-Za-z0-9_-]{1,128}',session_id):
                raise ValueError('회사 도구의 네이티브 세션 인증에 실패했습니다.')
            # Additional manager conversations belong to this organization in
            # the existing Hermes DB; the company secret alone cannot link one.
            from ai_agent.Hermes.engine.bridge import bridge
            session = bridge.call('session', {'id':session_id})['session']
            if session.get('company_id') != key:
                raise ValueError('회사 도구의 네이티브 세션 인증에 실패했습니다.')
        command = dict(payload.get('command', {}))
        if command.get('action') not in ('overview', 'recall', 'remember', 'propose', 'begin', 'finish', 'meeting', 'meeting_start', 'meeting_resume', 'meeting_proposal', 'meeting_read', 'meeting_turn', 'meeting_finish', 'run_start', 'run_finish') or '_owner' in command:
            raise ValueError('허용하지 않은 회사 도구 요청입니다.')
        command['_session'] = session_id
        return invoke('/api/admin/hermes/records', 'POST', command, token)
    if action == 'send':
        raise ValueError('AI 총괄은 Hermes 영구 세션의 chat/goal/loop를 사용합니다.')
    if action == 'meetings':
        from ai_agent.Hermes.engine.bridge import bridge
        meetings = invoke('/api/admin/meetings', token=token)
        records = invoke('/api/admin/hermes/records', 'POST', {'action': 'overview'}, token)
        team = invoke('/api/admin/team', token=token)
        job = bridge.call('status').get('job', {})
        live = job.get('meeting') or {}
        active = job.get('state') in ('starting', 'running', 'stopping')
        for meeting in meetings.get('meetings', []):
            if meeting.get('status') == 'running':
                # A saved agenda survives restart; it does not prove execution.
                meeting['execution_state'] = ('running' if active and live.get('id') == meeting['id']
                    else 'pending' if active and not live.get('id') and (live.get('company_id') == key or job.get('session_id') == native_id)
                    else 'interrupted')
        return {**meetings, **team, 'session_id': native_id, 'jobs': records.get('jobs', []), 'ventures': records.get('ventures', [])}
    if action == 'decision':
        venture = str(payload.get('venture_id', ''))
        if not re.fullmatch('[A-Za-z0-9_-]{1,100}', venture) or not isinstance(payload.get('approve'), bool):
            raise ValueError('사업안과 승인 여부를 확인하세요.')
        result = invoke('/api/admin/hermes/records', 'POST', {'action': 'decision', '_owner': True, 'venture_id': venture, 'approve': payload['approve']}, token)
        workspace=store.owned(store.project_folder(record),'workspaces/'+venture)
        if payload['approve']:workspace.mkdir(parents=True,exist_ok=True)
        return {**result,'session_id':native_id,'workspace':str(workspace)}
    if action != 'state': raise ValueError('지원하지 않는 대화 요청입니다.')
    control = invoke('/api/admin/control', token=token)
    result = {'session_id': native_id, 'ventures': control['ventures'],
              'progress': invoke('/api/store/info')}
    approved = [v for v in control['ventures'] if v.get('status') == 'approved']
    # Product identity belongs to approved ventures, not the retired storefront.
    result['progress'].pop('brand',None)
    result['progress']['approved'] = len(approved)
    result['progress']['ready_products'] = 0
    for venture in approved:
        key = str(venture.get('id', ''))
        if not re.fullmatch('[A-Za-z0-9_-]{1,100}', key): continue
        product = store.owned(store.project_folder(record), 'workspaces/' + key + '/dist/index.html')
        if product.is_file():
            result['progress']['ready_products'] += 1
            if result['progress']['ready_products'] == 1:
                result['progress'].update(preview_url='/_platform-output/' + key + '/dist/index.html', product_name=venture.get('name', key))
    return result
