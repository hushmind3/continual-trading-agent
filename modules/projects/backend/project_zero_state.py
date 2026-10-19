"""Authenticated workspace data over the original ASGI app, without a second server."""
from contextlib import asynccontextmanager
import json
import time
from fastapi import Header, HTTPException


def recover(db, meetings):
    for row in db.many("SELECT id FROM ceo_meetings WHERE status='running'"):
        meetings._finish(row['id'], 'failed', '앱 실행기가 재시작되어 회의가 중단됐습니다. 남은 발언은 실행되지 않았습니다. 새 회의를 시작하세요.')


def install(app):
    import database as db
    import meeting_engine as meetings
    import server
    import venture_engine
    if __package__:
        from . import project_zero_plans as plans
        from .project_zero_meeting import install as install_meeting,PREPARING
    else:
        import project_zero_plans as plans
        from project_zero_meeting import install as install_meeting,PREPARING
    install_meeting(app)
    # The original worker defaults to rules before awaiting a model call; an error is not a rules run.
    import ast,inspect,operations
    tree=ast.parse(inspect.getsource(operations.process_one));changed=0
    for node in ast.walk(tree):
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='mode' for t in node.targets) and isinstance(node.value,ast.Constant) and node.value.value=='rules':
            node.value=ast.Constant(value='unconfirmed');changed+=1
    if changed!=1:raise ValueError('원본 업무 실행 상태 구성이 변경됐습니다.')
    exec(compile(ast.fix_missing_locations(tree),inspect.getfile(operations.process_one),'exec'),operations.__dict__)
    life = app.router.lifespan_context
    @asynccontextmanager
    async def managed_life(instance):
        async with life(instance):
            # Native meeting tasks are in-memory and cannot survive a worker restart.
            plans.initialize(db)
            recover(db, meetings)
            yield
    app.router.lifespan_context = managed_life

    @app.post('/api/admin/platform/discussion-context')
    async def discussion_options(body: dict, x_project_zero_token: str | None = Header(None)):
        server.require_admin(x_project_zero_token)
        value=body.get('include_engine_context')
        if not isinstance(value,bool):raise HTTPException(422,'참/거짓 값을 입력하세요.')
        if db.one("SELECT id FROM ceo_meetings WHERE status='running' LIMIT 1"):
            raise HTTPException(409,'회의가 끝난 뒤 맥락 설정을 바꾸세요.')
        with db.LOCK,db.connect() as con:
            con.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",('platform_meeting_engine_context','true' if value else 'false'))
        return {'include_engine_context':value}

    @app.get('/api/admin/platform/workspace')
    async def workspace(x_project_zero_token: str | None = Header(None)):
        server.require_admin(x_project_zero_token)
        ventures = db.many('SELECT * FROM ventures ORDER BY rowid DESC LIMIT 20')
        for row in ventures: row['proposal'] = json.loads(row.pop('proposal_json'))
        ceo = await server.ceo_state(x_project_zero_token)
        team=await server.team_state(x_project_zero_token)
        for person in team['roles']:
            persona=meetings.TEAM.get(person['role'],{})
            person.update(persona=persona.get('style',''),responsibility=persona.get('priority',''))
        import ai_provider
        transport='hermes' if getattr(ai_provider,'platform_harness_connected',False) else 'native_api'
        return {'model_transport':transport,'plan_preparing':sorted(PREPARING),'plans': plans.latest(db), 'ceo': {'messages': ceo['messages']}, 'include_engine_context':db.settings().get('platform_meeting_engine_context','false')=='true',
                'team': team, 'meetings': meetings.latest(20),
                'ventures': ventures, 'active_product': venture_engine.live(),
                'jobs': db.many('SELECT id,role,type,title,status,result,error,mode,created_at,started_at,finished_at FROM jobs ORDER BY rowid DESC LIMIT 60'),
                'requests': [{'id': key, 'status': value['status'], 'error': value.get('error', ''),
                              'elapsed_seconds': round(time.monotonic()-value['started_at'])}
                             for key, value in list(server.CHAT_REQUESTS.items())[-10:]]}
