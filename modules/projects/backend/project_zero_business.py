"""Keep the bundled example out of new business ideas; preserve original approval gates."""
import functools
import json
import re


def request_options(system, user):
    import database as db
    try: data = json.loads(user)
    except (ValueError, TypeError): data = {}
    pure = isinstance(data, dict) and 'task' not in data and (any(k in data for k in ('prior_colleagues','minutes','previous_draft','_platform_turn','owner','owner_instruction','conversation')) or 'JSON' in system)
    shared = db.settings().get('platform_meeting_engine_context', 'false') == 'true'
    return {'context_scope': 'focused_discussion' if pure and not shared else 'native'}


def discussion_context(system, user, scope):
    if scope != 'focused_discussion': return system, user
    data = json.loads(user)
    if __package__:
        from .project_zero_context import clean_context
    else:
        from project_zero_context import clean_context
    data=clean_context(data)
    if 'prior_colleagues' in data:
        data = {**data, 'prior_colleagues': []}
        data.pop('recent_lessons', None)
    if data.get('_platform_turn')=='dialogue' or 'owner' in data:
        system+='\n현재 질문에 먼저 직접 답하세요. 의견 대화를 매번 회의·가설 검토·업무 배정으로 바꾸지 마세요. 기록에 없는 사실은 만들지 말고, 실행은 명시된 요청과 승인 범위를 따르세요.'
        return system,json.dumps(data,ensure_ascii=False)
    system += ('\n현재 앱의 대화·의견 작성 단계입니다. 현재 주제와 제공된 실제 사업 상태만 근거로 삼으세요. '
               '과거 개발 점검이나 예제 상품을 이번에 선택된 사업으로 간주하지 마세요. '
               '각 전문가는 먼저 독립적으로 자기 담당 관점의 가설·반론·검증안을 작성하고 CEO가 실행안으로 종합합니다. '
               'CPO는 고객·제품 요구사항을 담당하며 코드·명령·도구 호출문을 발언으로 출력하지 마세요. '
               '검토 중 실제 도구 실행은 없으며 필요한 조사는 승인할 업무로 제안하세요. '
               '동료의 추정은 검증된 사실이 아니며 수익 달성을 보장하지 마세요.')
    return system, json.dumps(data, ensure_ascii=False)


def install(venture):
    import ai_provider
    ai_provider.platform_request_options = request_options
    # BASE is supplied to every new model proposal as previous_draft by the original app.
    venture.BASE = {key: 0 if key == 'price' else '' for key in venture.FIELDS}
    normalize = venture._normalize
    @functools.wraps(normalize)
    def checked(raw, old):
        result = normalize(raw, old)
        values = json.loads(re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip(), flags=re.I).strip())
        if not old.get('name') and (type(values.get('price')) is not int or not 0 <= values['price'] <= 1000000):
            raise ValueError('새 사업 초안의 가격 가설이 없습니다.')
        for key in venture.FIELDS:
            value = values.get(key)
            if key != 'price' and isinstance(value, str) and 1 <= len(value.strip()) <= 1000:
                result[key] = value.strip()
        missing = [key for key in venture.FIELDS if key != 'price' and not str(result.get(key, '')).strip()]
        if missing: raise ValueError('사업 초안의 필수 내용이 없습니다: ' + ', '.join(missing))
        return result
    venture._normalize = checked
