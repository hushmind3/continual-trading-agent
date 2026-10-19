"""Do not recycle an unselected bundled example from generated history as a user fact."""
import json
import re

def role_reference(instruction):
    terms=re.search(r'CPO|CTO|CEO|CMO|CFO|QA|고객.?담당|설계.*누가',instruction,re.I)
    question=re.search(r'역할|담당|누가|설명|무슨|무엇|뭘',instruction)
    scoped=re.search(r'최근|지난|앞서|그(?:거|것|\s*홈페이지|\s*설계)|이(?:\s*사업|\s*제품|\s*프로젝트)|우리\s*사업|진행\s*상황|실행\s*결과',instruction)
    return bool(terms and question and not scoped)

def clean_context(value):
    value=dict(value)
    instruction=str(value.get('owner_instruction') or value.get('owner') or value.get('topic') or '')
    if (value.get('_platform_turn')=='dialogue' or 'owner' in value) and role_reference(instruction):
        if __package__:
            from .project_zero_roles import ROLES
        else:
            from project_zero_roles import ROLES
        return {'owner_instruction':instruction,'_platform_turn':'dialogue','context_kind':'role_reference',
                'role_catalog':{key:{'persona':style,'responsibility':priority} for key,(style,priority) in ROLES.items()},
                'reference_scope':'등록된 역할의 일반 책임을 설명하는 질문입니다. 과거 사업·회사의 실적·현재 업무 진행 상태를 가정하지 마세요.'}
    active=value.get('active_venture') or {}
    if str(active.get('name','')).casefold()=='dealpage':return value
    def example(item):return 'dealpage' in json.dumps(item,ensure_ascii=False).casefold()
    for key in ('recent_chat','recent_meetings','learned_lessons','recent_lessons','actual_outcomes','lessons','previous_job_outcomes'):
        items=value.get(key)
        if isinstance(items,list):value[key]=[item for item in items if isinstance(item,dict) and item.get('speaker')=='owner' or not example(item)]
        elif isinstance(items,dict) and example(items):value.pop(key)
    pending=value.get('pending_venture')
    if pending and example(pending) and 'dealpage' not in instruction.casefold():value['pending_venture']=None
    if 'dealpage' in instruction.casefold():
        value['example_reference']='DealPage는 원본에 포함된 제안서·견적서 작성 예제입니다. 이 이름을 질문한 것과 사업으로 선택·승인한 것은 다릅니다.'
    value['evidence_scope']='앱 내부 주문·장부 수치는 이 앱의 기록입니다. 사용자의 다른 사업·고객·매출 현황으로 확대 해석하지 마세요. 이전 AI 발언은 사용자 선택이나 실적 증거가 아닙니다.'
    return value
