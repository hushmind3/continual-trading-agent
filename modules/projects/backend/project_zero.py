"""Compatibility for PROJECT ZERO's existing workflow; no copied UI, DB, or business engine."""
import ast
import functools
import inspect
import json
import re


def _negated(message):
    return bool(re.search(r'(?:만들|생성|제안|추천|수정|진행|초안).{0,8}(?:하지\s*마|하지\s*말|말아|말고|지\s*마)', message))


def is_new_request(message, original):
    if _negated(message): return False
    if re.search(r'설명|비교|의미|뭐야|어때|왜|진행\s*상황', message) and not re.search(r'제안|추천|찾아|만들|기획|작성|발굴', message): return False
    return original(message) or bool(re.search(r'벌\s*거리|수익.*(?:아이디어|추천)|월.*(?:벌|수익).*(?:의논|추천|제안|찾)', message))


def is_revision(message, pending):
    if not pending or _negated(message): return False
    return bool(re.search(r'(?:수정|바꿔|고쳐|변경|조정|낮춰|높여|줄여|올려|내려)', message))


def provider_system(system):
    system=system.replace('이 시스템에서 할 수 없는 외부 검색, 코드 수정, 배포, 광고 집행은 수행했다고 주장하지 마세요.',
        '현재 Hermes에 설정된 도구와 권한으로 요청받은 분석·파일 작업·검증을 수행하세요. '
        '실제 도구 결과로 확인한 작업만 완료했다고 보고하세요. '
        '이미 명시된 파일을 읽을 때는 tool_describe로 read_file 명세를 확인한 뒤 해당 파일을 읽으세요. '
        'tool_search에 파일명을 넣어 검색을 반복하지 마세요. 보고에는 확인한 파일과 근거 줄을 표시하세요. '
        '외부 공개·배포·광고 구매·메일 발송은 소유자의 명시적 승인 후에만 수행하세요.')

    if __package__:
        from .project_zero_roles import system_persona
    else:
        from project_zero_roles import system_persona
    return system_persona(system)

def failed_plan(message):
    return '요청한 작업은 실행하지 않았습니다. 모델 응답 처리 오류를 해결한 뒤 다시 요청하세요.', []


def install():
    import ceo_engine as ceo
    import venture_engine as venture
    if __package__:
        from .project_zero_business import install as install_business
        from .project_zero_state import install as install_workspace
    else:
        from project_zero_business import install as install_business
        from project_zero_state import install as install_workspace
    if __package__:
        from .project_zero_roles import install as install_roles,CONVERSATION
        from .project_zero_context import clean_context
    else:
        from project_zero_roles import install as install_roles,CONVERSATION
        from project_zero_context import clean_context
    import server
    install_roles()
    install_business(venture)
    install_workspace(server.app)
    original = ceo._is_new_venture_request
    ceo._is_new_venture_request = lambda message: is_new_request(message, original)
    context = ceo._context
    @functools.wraps(context)
    def current_context(message):
        value = json.loads(context(message))
        import meeting_engine
        value.update(pending_venture=venture.current_pending(), active_venture=venture.live(),
            recent_meetings=meeting_engine.latest(2) if any(term in message for term in ('회의','실행안','직원 의견','팀 의견','발언','승인안')) else [])
        value['_platform_turn']='dialogue'
        return json.dumps(clean_context(value), ensure_ascii=False, default=str)
    ceo._context = current_context
    # Replace only the over-broad revision condition; retain the original transaction/approval flow.
    tree = ast.parse(inspect.getsource(ceo.talk))
    changes = 0
    failures = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'revise' for t in node.targets):
            node.value = ast.parse('_platform_is_revision(message, pending)', mode='eval').body; changes += 1
        if isinstance(node, ast.ExceptHandler):
            for statement in ast.walk(node):
                if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Call) and isinstance(statement.value.func, ast.Name) and statement.value.func.id == 'fallback_plan':
                    statement.value.func.id = '_platform_failed_plan'; failures += 1
    if changes != 1 or failures != 1: raise ValueError('프로젝트제로의 대화 분기가 변경돼 호환 어댑터를 확인해야 합니다.')
    ceo._platform_is_revision = is_revision
    ceo._platform_failed_plan = failed_plan
    exec(compile(ast.fix_missing_locations(tree), inspect.getfile(ceo.talk), 'exec'), ceo.__dict__)
    prompt = ceo.planning_system_prompt
    @functools.wraps(prompt)
    def planning_prompt():
        return CONVERSATION+'\n'+prompt().replace(
            'agent_task는 정보/기획/문서 제작만 가능하며 코드 변경·외부 조사·광고 구매·배포·메일 발송을 직접 수행하지 못합니다.',
            'agent_task는 현재 Hermes에 설정된 도구와 권한으로 요청한 분석·파일 작업·검증을 수행할 수 있습니다. '
            '실행 결과가 있을 때만 완료로 보고하고 광고 구매·외부 공개·메일 발송은 소유자의 명시적 승인이 필요합니다.')
    ceo.planning_system_prompt = planning_prompt
    decide = venture.decide
    @functools.wraps(decide)
    def decision(*args, **kwargs):
        result = decide(*args, **kwargs)
        old = result.get('reply', '')
        new = old.replace('현재 하네스에는 새로운 프로그램의 코드 작성·테스트·배포 도구가 없으므로 실제 서비스 공개는 하지 않았습니다.',
            '현재는 사업 검토와 기술 준비를 등록한 단계이며 제품 제작·검증·배포를 완료하지 않았습니다. '
            '구체적인 구현 요청은 설정된 Hermes 도구와 권한으로 진행할 수 있습니다.')
        if new != old:
            import database as db
            with db.LOCK, db.connect() as con:
                con.execute("UPDATE ceo_messages SET body=? WHERE rowid=(SELECT rowid FROM ceo_messages WHERE speaker='ceo' AND body=? ORDER BY rowid DESC LIMIT 1)", (new, old))
            result['reply'] = new
        return result
    venture.decide = decision
