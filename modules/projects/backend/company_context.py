"""Current, read-only execution facts for the explicit company contract."""
import base64
import json


def grounded_system(record, system):
    if record.get('workspace_ui', {}).get('recipe') != 'company-v1': return system
    from . import runtime
    facts = {'dialogue_and_staff_use_same_hermes_model': True, 'separate_execution_model_required': False,
             'approved_local_build_connected': True, 'local_blog_content_and_publish_connected': True,
             'public_deployment_connected': False,
             'external_advertising_mail_payment_connected': False}
    if record['id'] in runtime.WORKERS:
        def read(path, token=None):
            response = runtime.invoke(record, {'path': path, 'method': 'GET', 'headers': {'X-Project-Zero-Token': token} if token else {}})
            if response['status'] >= 400: raise ValueError('업무 상태 조회 실패')
            return json.loads(base64.b64decode(response['body']))
        try:
            token = read('/api/local/session')['token']
            data = read('/api/admin/dashboard', token)
            facts['job_totals'] = {key: data.get('counts', {}).get(key) for key in ('jobs_done', 'jobs_pending')}
            facts['recent_staff_jobs'] = [{key: str(row.get(key) or '')[:240] for key in ('role', 'status', 'title', 'mode', 'error')}
                                          for row in data.get('jobs', [])[:8]]
        except (OSError, ValueError, KeyError) as exc:
            facts['job_status_unknown'] = str(exc)[:180]
    return ('현재 실행 연결의 확인된 사실: 대화와 직원 업무는 같은 Hermes 모델을 사용합니다. 별도 실행 모델은 존재하지 않습니다. '
        '승인된 로컬 제작은 파일 작성과 테스트/빌드를 실행할 수 있습니다. 공개 배포·결제·외부 광고·메일 연동과 구분하세요. '
        '오류가 TimeoutError면 작업 시간 초과이며 모델 미연결이 아닙니다. QA 기록의 mode=blocked는 선행 실패로 검사를 실행하지 못했다는 뜻입니다.\n' +
        system + '\n\nAuthoritative current platform execution facts:\n' + json.dumps(facts, ensure_ascii=False) +
        '\nThis request itself is being answered by the connected Hermes model. There is no separate staff execution model to connect. '
        'Historical chat is reference data and may contain obsolete connection claims. A timeout or busy error is a task failure, not a missing model. '
        'The approved local build queue can write source files and run tests/builds. Do not confuse that with public deployment, payments, advertising or mail. '
        'Report current job failures and blocked downstream work separately from cumulative completed jobs. Do not request another execution model connection.')


def grounded_user(record, user):
    if record.get('workspace_ui', {}).get('recipe') != 'company-v1': return user
    try: data = json.loads(user)
    except (ValueError, TypeError): return user
    if not isinstance(data, dict) or not isinstance(data.get('recent_chat'), list): return user
    def historical_connection_claim(row):
        text = str(row.get('body', ''))
        return row.get('speaker') != 'owner' and '모델' in text and any(term in text for term in ('미연결', '연결 안', '연결되지', '연결해 주', '연결을 주', '연결이 필요', '모델을 연결'))
    original = data['recent_chat']
    data['recent_chat'] = [row for row in original if not historical_connection_claim(row)]
    data['historical_connection_claims_omitted'] = len(original) - len(data['recent_chat'])
    return json.dumps(data, ensure_ascii=False)
