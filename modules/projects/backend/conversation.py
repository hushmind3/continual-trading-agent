"""Original company conversation API through the existing platform router."""
import base64
import json
import re
from . import runtime, store


def call(key, payload, origin=None):
    record = store.read(key)
    if record.get('stage') != 'ready' or record.get('workspace_ui', {}).get('recipe') != 'company-v1' or not record.get('harness', {}).get('enabled'):
        raise ValueError('연결된 AI 총괄 대화가 없습니다.')

    def invoke(path, method='GET', body=None, token=None):
        value = {'path': path, 'method': method, 'headers': {'X-Project-Zero-Token': token} if token else {}}
        if body is not None:
            value['body'] = base64.b64encode(json.dumps(body, ensure_ascii=False).encode()).decode()
            value['headers']['Content-Type'] = 'application/json'
        response = runtime.invoke(record, value, origin)
        result = json.loads(base64.b64decode(response['body']))
        if response['status'] >= 400: raise ValueError(result.get('detail', '앱 대화 요청에 실패했습니다.'))
        return result

    token = invoke('/api/local/session')['token']
    action = payload.get('action', 'state')
    if action == 'send':
        message = str(payload.get('message', '')).strip()
        if not message or len(message) > 12000: raise ValueError('메시지는 1~12,000자입니다.')
        return invoke('/api/admin/ceo/chat/submit', 'POST', {'message': message}, token)
    if action == 'decision':
        venture = str(payload.get('venture_id', ''))
        if not re.fullmatch('[A-Za-z0-9_-]{1,100}', venture) or not isinstance(payload.get('approve'), bool):
            raise ValueError('사업안과 승인 여부를 확인하세요.')
        return invoke('/api/admin/ventures/' + venture + '/decision', 'POST', {'approve': payload['approve']}, token)
    if action != 'state': raise ValueError('지원하지 않는 대화 요청입니다.')
    history = invoke('/api/admin/ceo', token=token)
    control = invoke('/api/admin/control', token=token)
    result = {'messages': history['messages'], 'ventures': control['ventures']}
    if request_id := payload.get('request_id'):
        if not re.fullmatch('[a-f0-9]{32}', str(request_id)): raise ValueError('대화 요청 ID를 확인하세요.')
        try: result['request'] = invoke('/api/admin/ceo/chat/status/' + request_id, token=token)
        except ValueError as exc: result['request'] = {'status': 'failed', 'error': str(exc)}
    return result
