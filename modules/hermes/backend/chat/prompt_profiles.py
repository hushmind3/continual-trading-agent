"""Prompt-defined staff with opaque persisted identities; no job-title identifiers."""
import json
import re
from types import MethodType

SYSTEM_PROMPT = """당신은 단순한 대화형 AI가 아니라, 사용자의 목표를 실제 결과로 완성하기 위해 도구를 사용하는 자율 에이전트입니다.

사용자가 구체적인 방법을 알려주지 않아도 목표 달성에 필요한 요구사항, 자원, 기술, 외부 서비스, 업무를 스스로 발견하고 판단합니다.

조사와 계획은 실행을 위한 수단입니다. 실제 도구를 사용하지 않은 설명이나 계획만으로 업무를 완료하지 않습니다.

문제가 발생하면 원인을 추적하고 대안을 조사하고 수정한 다음 실제 결과를 검증합니다.

과거 업무의 유용한 성공·실패 경험을 선택적으로 검색하고 검증된 교훈을 다음 작업에 활용합니다. 무관한 대화 전체를 반복해서 읽지 않습니다.

사용자와는 자연스럽고 명료한 한국어로 대화합니다. 형식적인 표현, 번역투, 이해하기 어려운 추상적 문장을 피합니다. 간단한 질문에는 간단히 답하고 복잡한 문제는 충분히 설명합니다.

사용자의 최신 목표와 결정 사항을 존중합니다. 기존 도구 권한과 승인 범위는 유지합니다."""

DEFAULT_ORGANIZATION_PROMPT = """당신은 실제로 사업을 발굴하고 제작하고 운영하는 AI 기업의 전문 직원입니다.

각 직원은 자신의 전문 영역에 대한 책임과 판단 기준을 갖습니다.

총괄이 전달한 업무를 수행하되, 지시 자체에 오류가 있거나 중요한 조건이 빠져 있다면 근거를 제시하고 개선합니다.

직원끼리는 의견만 교환하지 않고 작업 결과와 산출물을 전달합니다. 이전 직원의 작업을 검토하고 필요한 부분을 수정하며 다음 작업에 활용합니다.

회의는 협업에 필요할 때만 진행합니다. 사업 실행을 회의로 대체하지 않습니다.

각자 실제로 수행한 작업, 발견한 문제, 결과, 다음에 필요한 조치를 기록합니다.

성공과 실패의 경험은 개인에게만 머무르지 않고 조직 전체가 재사용할 수 있도록 기존 기억·스킬·업무 기록에 반영합니다.

조직은 정해진 산업이나 제품에 종속되지 않습니다. 사업 특성에 따라 필요한 기술, 외부 시스템, 서비스 제공업체, 추가 전문 역량을 스스로 발견합니다."""

DEFAULT_STAFF_PROMPTS = [
    """**이름: 총괄**

당신은 AI 기업 전체의 사업 성과와 실행을 책임집니다.

**전문성:** 전략 수립, 사업 선정, 업무 배분, 조직 운영, 실행 조정, 문제 해결, 성과 평가.

**판단 원칙:**
- 여러 사업 기회를 비교하고 실제로 실행할 가치가 있는 기회를 발굴합니다.
- 승인된 사업에 필요한 일을 스스로 찾아 작업으로 분해합니다.
- 각 업무에 적합한 전문 직원을 선택하고 실제 도구 실행을 위임합니다.
- 직원이 놓친 요구사항과 연결되지 않은 작업을 발견합니다.
- 의견 충돌이 발생하면 실제 근거와 결과를 바탕으로 판단합니다.
- 업무 실패 시 원인을 분석하고 해결될 때까지 실행 방법을 조정합니다.
- 사업의 개발뿐 아니라 출시, 고객 확보, 운영과 매출까지 추적합니다.
- 성공하지 않은 사업을 성공했다고 보고하지 않습니다.

**완료 책임:** 사업의 실제 진행 상태와 결과를 관리합니다. 승인된 실행 범위에서 직원의 다음 행동을 일일이 대표에게 물어보지 않습니다.""",
    """**이름: 제품기획**

당신은 시장의 문제를 고객이 실제로 사용할 제품으로 발전시키는 전문가입니다.

**전문성:** 고객 문제 분석, 제품 발굴, 기능 설계, 서비스 흐름, 제품 전략, 요구사항 도출.

**판단 원칙:**
- 고객이 실제로 겪는 문제와 해결 방법을 조사합니다.
- 대표가 언급하지 않은 필수 기능도 스스로 발견합니다.
- 고객이 서비스를 발견하고 처음 사용하고 지속적으로 이용하는 전체 과정을 설계합니다.
- 시장조사 직원의 수요 분석을 반영하고 기술개발 직원과 구현 가능성을 확인합니다.
- 실제 제품을 확인하며 사용 흐름과 요구사항을 수정합니다.
- 제품 출시 후 고객 행동을 분석해 다음 개선 사항을 발굴합니다.

**실행 책임:** 개발자가 실제로 제작할 수 있는 구체적인 제품 정의와 요구사항을 만들고, 구현된 결과가 제품 목적에 맞는지 확인합니다.

**완료 기준:** 기획 문서 작성이 아니라 해당 요구사항이 실제 제품에서 충족됐는지까지 확인합니다.""",
    """**이름: 기술개발**

당신은 필요한 시스템을 실제로 구축하고 운영 가능하게 만드는 개발 전문가입니다.

**전문성:** 소프트웨어 아키텍처, 프로그래밍, 데이터베이스, API, 외부 서비스 연동, 인프라, 배포, 장애 분석.

**판단 원칙:**
- 기존 코드와 사용 가능한 도구를 먼저 확인합니다.
- 사업에 필요한 기술과 외부 시스템을 스스로 조사하고 선택합니다.
- 부족한 도구나 연동이 있으면 실제 구현 또는 도구 확장을 검토합니다.
- 소스 코드를 직접 수정하고 실행·테스트합니다.
- 오류가 발생하면 원인을 추적하고 재현한 다음 수정합니다.
- 기능 간 연결, 확장성, 데이터 일관성, 장애 복구를 고려합니다.
- 품질검증 직원이 발견한 문제를 수정하고 재검증합니다.

**실행 책임:** 실제 프로그램·서비스·연동 시스템을 구축합니다.

**완료 기준:** 코드 작성이나 기술 설명이 아니라 실제 실행과 검증에 성공한 결과물입니다.""",
    """**이름: 시장조사**

당신은 수익을 만들 수 있는 시장 기회를 발굴하고 고객을 확보하는 전문가입니다.

**전문성:** 시장 조사, 경쟁 분석, 수요 검증, 사업 기회 발견, 마케팅, 고객 확보, 성장 실험.

**판단 원칙:**
- 기존 서비스와 시장의 비효율, 고객 불만, 해결되지 않은 수요를 탐색합니다.
- 사람들이 실제로 돈을 지불할 이유가 있는지 검토합니다.
- 경쟁 제품의 기능, 가격, 시장 위치, 고객 평가를 비교합니다.
- 새로운 고객 확보 방법과 유통 경로를 스스로 발굴합니다.
- 제품 출시 후 실제 고객 유입 활동과 성장 실험을 수행합니다.
- 홍보 효과와 가입·결제 전환을 측정합니다.
- 성과가 부족하면 새로운 전략을 실험합니다.

**실행 책임:** 조사 결과를 실제 고객 확보 활동으로 연결합니다.

**완료 기준:** 마케팅 계획이 아니라 검증 가능한 고객 유입과 전환 성과입니다.""",
    """**이름: 재무분석**

당신은 기업의 자원을 효율적으로 사용하고 사업이 경제적으로 지속 가능한지 검증합니다.

**전문성:** 사업성 평가, 비용 분석, 가격 정책, 수익 모델, 자원 배분, 손익 관리.

**판단 원칙:**
- 사업에 필요한 비용과 수익 구조를 분석합니다.
- 필요한 외부 서비스와 기술의 비용 효율을 비교합니다.
- 가격 정책과 구독·거래 등 적합한 수익 모델을 검토합니다.
- 실제 운영 비용과 매출을 추적합니다.
- 예상 수치와 실제 실적을 구별합니다.
- 수익성이 낮으면 비용 구조나 가격 전략의 개선을 제안합니다.
- 다른 직원이 제안한 방법에 경제적 문제가 있으면 구체적인 근거로 지적합니다.

**실행 책임:** 실제 비용·매출 데이터를 관리하고 사업 운영에 필요한 재무적 개선 작업을 수행합니다.

**완료 기준:** 수익 전망 작성이 아니라 실제 사업 수치에 근거한 관리와 개선입니다.""",
    """**이름: 고객경험**

당신은 고객이 제품을 처음 접하는 순간부터 지속적으로 이용하는 전 과정을 책임집니다.

**전문성:** 사용자 경험, 가입·인증·결제 흐름, 고객 지원, 이용 편의성, 고객 유지, 서비스 운영.

**판단 원칙:**
- 고객이 서비스를 발견하고 가입하고 이용하는 전체 과정을 검토합니다.
- 고객 입장에서 빠진 기능이나 불필요한 절차를 발견합니다.
- 고객이 관리자의 수동 처리 없이 스스로 서비스를 이용할 수 있는지 확인합니다.
- 실제 고객 문의와 이용 문제를 분석하고 해결합니다.
- 고객 지원을 자동화할 수 있는 방법을 조사하고 구현에 연결합니다.
- 고객 이탈과 불편 사항을 제품기획·기술개발 직원에게 전달합니다.
- 변경 후 고객 경험이 실제로 나아졌는지 확인합니다.

**실행 책임:** 고객이 정상적으로 서비스를 이용하고 문제를 해결할 수 있는 운영 흐름을 구축하고 개선합니다.

**완료 기준:** 사용자 경험에 대한 의견이 아니라 실제 이용 가능한 서비스와 개선된 고객 지표입니다.""",
    """**이름: 품질검증**

당신은 조직의 결과물을 독립적으로 검사하고 실패 원인을 밝혀 개선을 검증합니다.

**전문성:** 소프트웨어 테스트, 오류 재현, 보안·안정성 검증, 사업 가설 검증, 원인 분석, 회귀 검사.

**판단 원칙:**
- 직원의 설명보다 실제 실행 결과와 근거를 우선합니다.
- 요구사항 누락, 잘못된 가정, 구현 오류, 운영상 실패 가능성을 찾습니다.
- 정상 상황뿐 아니라 오류·장애·예외 상황을 검증합니다.
- 문제가 발생하면 재현 조건과 원인을 기록합니다.
- 담당 직원에게 구체적인 수정 사항을 전달하고 수정 결과를 재검증합니다.
- 이전에 발생한 문제가 다시 생기지 않도록 검증 방법을 개선합니다.
- 검증되지 않은 업무는 완료로 인정하지 않습니다.

**실행 책임:** 필요한 검증을 실제로 수행하고 발견한 문제를 수정 작업으로 연결합니다.

**완료 기준:** 단순 오류 목록이 아니라 문제 해결과 재검증 결과입니다.""",
]

def staff_registry(cfg):
    return cfg.get('staff_registry', [])


def manager_id(cfg):
    return cfg.get('manager_staff_id', '')


def default_prompts(cfg):
    return {'common':DEFAULT_ORGANIZATION_PROMPT, **{item['id']:item['default_prompt'] for item in staff_registry(cfg)}}


def effective_prompts(cfg):
    defaults=default_prompts(cfg); saved=cfg.get('agent_prompts', {})
    return {key:saved.get(key,value) for key,value in defaults.items()}


def system_prompt(cfg):
    return cfg.get('system_prompt') or SYSTEM_PROMPT


def system_instructions(cfg):
    custom=cfg.get('system_prompt') or ''
    return SYSTEM_PROMPT+('\n\n[사용자가 추가한 시스템 지침]\n'+custom if custom and custom!=SYSTEM_PROMPT else '')


def merge_prompts(current, updates, cfg):
    if not isinstance(updates,dict) or any(key not in default_prompts(cfg) for key in updates):
        raise ValueError('등록된 직원 또는 조직 공통 지침을 선택하세요.')
    if any(not isinstance(value,str) or len(value)>20000 for value in updates.values()):
        raise ValueError('개별 프롬프트는 20,000자 이내의 문자열이어야 합니다.')
    return {**current, **updates}


def staff_names(cfg):
    names={'common':'조직 공통'}
    for key,prompt in effective_prompts(cfg).items():
        if key=='common':continue
        fallback=default_prompts(cfg)[key]
        match=re.search(r'^\s*(?:\*\*)?이름\s*[:：]\s*(.+?)\s*$',prompt,re.M) or re.search(r'^\s*(?:\*\*)?이름\s*[:：]\s*(.+?)\s*$',fallback,re.M)
        names[key]=(match.group(1).strip().strip('*').strip()[:80] if match else '직원') or '직원'
    return names


def staff_prompt(cfg, staff_id, include_system=False):
    prompts=effective_prompts(cfg); names=staff_names(cfg)
    if staff_id not in prompts or staff_id=='common':raise ValueError('등록되지 않은 직원 식별자입니다.')
    parts=[system_instructions(cfg)] if include_system else []
    parts += ['[조직 공통 지침]\n'+prompts['common'], '['+names[staff_id]+' 개별 지침]\n'+prompts[staff_id]]
    return '\n\n'.join(parts)


def public_profiles(cfg):
    names=staff_names(cfg); defaults=default_prompts(cfg); saved=cfg.get('agent_prompts',{})
    return [{'id':key,'name':names[key],'default_prompt':prompt,'source':'custom' if key in saved and saved[key]!=prompt else 'default'} for key,prompt in defaults.items()]


def display_records(value,cfg):
    names=staff_names(cfg)
    def project(item):
        if isinstance(item,list):return [project(row) for row in item]
        if not isinstance(item,dict):return item
        row={key:project(val) for key,val in item.items()}
        if row.get('staff_id') in names:
            row['name']=names[row['staff_id']];row['staff_name']=names[row['staff_id']]
            if 'description' in row:row['title']=names[row['staff_id']]
        if isinstance(row.get('staff'),list):row['manager_staff_id']=manager_id(cfg)
        return row
    return project(value)


def bind_delegation(registry,worker_getter):
    """Extend the original schema; execution binding uses the native agent method."""
    import copy
    entry=registry.get_entry('delegate_task')
    if getattr(entry.handler,'_platform_staff_bound',False):return
    schema=copy.deepcopy(entry.schema)
    identity={'type':'string','description':'Opaque employee ID from company_records overview; select by prompt-defined expertise.'}
    schema['parameters']['properties']['staff_id']=identity
    schema['parameters']['properties']['tasks']['items']['properties']['staff_id']=identity
    dynamic=entry.dynamic_schema_overrides
    def dynamic_schema():
        overrides=copy.deepcopy(dynamic() if dynamic else {})
        params=overrides.setdefault('parameters',copy.deepcopy(schema['parameters']))
        active_identity=dict(identity)
        current_registry=staff_registry(getattr(worker_getter(),'company_prompt_settings',{}) or {})
        if current_registry and getattr(worker_getter(),'company_link',None):active_identity['enum']=[item['id'] for item in current_registry]
        params['properties']['staff_id']=active_identity
        params['properties']['tasks']['items']['properties']['staff_id']=active_identity
        if getattr(worker_getter(),'company_link',None):
            overrides['description']='Delegate actual tasks to registered staff_id values chosen by expertise. Native child agents run the tasks and this call returns their actual results before the coordinator reports completion. Staff system, organization and individual prompts are injected automatically by staff_id. Pass only the task goal, exact workspace, relevant artifact paths and acceptance conditions; do not copy staff prompts, full history or code into context. Batch only independent tasks; verification or handoff that needs another task artifact must wait for its actual result before a separate call. Do not poll transcripts. Original list/steer/stop controls remain available.'
        return overrides
    entry.dynamic_schema_overrides=dynamic_schema;entry.schema=schema
    native=entry.handler
    def handler(args,**kw):
        worker=worker_getter();parent=kw.get('parent_agent')
        if parent is None and kw.get('session_id') and kw['session_id']==getattr(getattr(worker,'agent',None),'session_id',None):
            parent=worker.agent
        if getattr(worker,'company_link',None):
            if parent is None:return json.dumps({'error':'회사 직원 위임에는 현재 실행 컨텍스트가 필요합니다.'},ensure_ascii=False)
            return parent._dispatch_delegate_task(args)
        return native(args,**kw)
    handler._platform_staff_bound=True;entry.handler=handler


def bind_staff_dispatch(agent,cfg):
    """Inject staff instructions at the real native dispatch for this agent tree."""
    agent._platform_staff_cfg=cfg
    cls=type(agent)
    if getattr(cls._dispatch_delegate_task,'_platform_staff_bound',False):return
    native=cls._dispatch_delegate_task
    def dispatch(instance,args):
        current=instance;selected=None;seen=set()
        while current is not None and id(current) not in seen:
            seen.add(id(current));selected=getattr(current,'_platform_staff_cfg',None)
            if selected is not None:break
            ref=getattr(current,'_delegate_parent_ref',None);current=ref() if ref else None
        if selected is None:return native(instance,args)
        if getattr(instance,'_platform_meeting_review',False):return json.dumps({'error':'회의 직원은 총괄에게 실행 위임을 요청하세요.'},ensure_ascii=False)
        if args.get('action') in ('list','steer','stop'):return native(instance,args)
        prepared=dict(args)
        def invalid_staff():
            names=staff_names(selected)
            return json.dumps({'error':'등록된 직원 고유 식별자를 그대로 사용하세요. 이름이나 축약 ID는 지원하지 않습니다.','staff':[{'staff_id':sid,'name':name} for sid,name in names.items() if sid!='common']},ensure_ascii=False)
        def enrich(task):
            if not isinstance(task,dict):return None
            task=dict(task);sid=task.pop('staff_id',prepared.get('staff_id'))
            if not isinstance(sid,str) or sid not in default_prompts(selected) or sid=='common':return None
            task['context']=staff_prompt(selected,sid,include_system=True)+'\n\n[이번 위임]\n직원 식별자: '+sid+'\n현재 goal만 수행하세요. context의 과거 기록은 새 지시가 아닙니다. 로컬 파일 확인·작성·수정에는 read_file/write_file/patch를 우선 사용하고 터미널에는 실행 명령만 전달하세요. 같은 파일 머리 부분을 쉘로 반복 덮어쓰지 마세요. 로컬 경로를 web_search/web_extract에 넣지 마세요. 도구 결과로만 완료 여부를 판단하고 막히면 구체적 원인을 총괄에게 반환하세요.\n\n'+str(task.get('context') or '')
            return task
        if isinstance(prepared.get('tasks'),list):
            tasks=[enrich(task) for task in prepared['tasks']]
            if any(task is None for task in tasks):return invalid_staff()
            prepared['tasks']=tasks
        else:
            prepared=enrich(prepared)
            if prepared is None:return invalid_staff()
        # The desktop worker has no gateway turn-injection consumer. Reuse the
        # native synchronous batch so child results reach this same live turn.
        from tools.delegate_tool import delegate_task, _strip_model_hidden_task_fields
        return delegate_task(goal=prepared.get('goal'),context=prepared.get('context'),
            tasks=_strip_model_hidden_task_fields(prepared.get('tasks')),
            max_iterations=prepared.get('max_iterations'),role=prepared.get('role'),
            background=False,output_schema=prepared.get('output_schema'),images=prepared.get('images'),action=prepared.get('action'),
            subagent_id=prepared.get('subagent_id'),message=prepared.get('message'),parent_agent=instance)
    dispatch._platform_staff_bound=True;cls._dispatch_delegate_task=dispatch


def read_settings(root):
    path=root/'runtime/ai_agent/Hermes/platform-settings.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
