"""Isolated original-app workflow suite; invoked only by verify_project_zero.py."""
import json
import os
from unittest.mock import AsyncMock
__test__ = os.environ.get('PLATFORM_PROJECT_ZERO_WORKFLOW_TEST') == '1'
if __test__:
    from test_end_to_end import app, live


def seed_pending(db):
    proposal={'name':'Unbuilt service','product':'검토 단계 제품','price':19000,'problem':'고객 문제','market':'가설','validation':'검증 예정','execution':'승인 필요'}
    with db.connect() as con:
        con.execute('INSERT INTO ventures(id,created_at,name,proposal_json,status,mode) VALUES(?,?,?,?,?,?)',
                    ('venture_probe',db.now(),proposal['name'],json.dumps(proposal,ensure_ascii=False),'pending','llm'))


def test_greeting_with_pending_plan_keeps_it_unchanged(live,monkeypatch):
    client,headers,db=live;seed_pending(db)
    import ai_provider
    monkeypatch.setattr(ai_provider,'status',AsyncMock(return_value={'mode':'hermes','name':'test','endpoint':''}))
    mock=AsyncMock(return_value='{"reply":"안녕하세요. 무엇을 도와드릴까요?","tasks":[]}')
    monkeypatch.setattr(ai_provider,'compose',mock)
    response=client.post('/api/admin/ceo/chat',headers=headers,json={'message':'그럼 안녕'})
    assert response.status_code==200
    assert response.json()['jobs']==[] and '안녕하세요' in response.json()['reply']
    assert db.one('SELECT count(*) AS n FROM ventures')['n']==1
    assert db.one("SELECT status FROM ventures WHERE id='venture_probe'")['status']=='pending'
    assert db.one('SELECT count(*) AS n FROM ceo_meetings')['n']==0
    mock.assert_awaited_once()


def test_negated_proposal_request_never_creates_a_venture(live,monkeypatch):
    client,headers,db=live
    import ai_provider
    monkeypatch.setattr(ai_provider,'status',AsyncMock(return_value={'mode':'hermes','name':'test','endpoint':''}))
    monkeypatch.setattr(ai_provider,'compose',AsyncMock(return_value='{"reply":"초안은 만들지 않고 답변만 하겠습니다.","tasks":[]}'))
    response=client.post('/api/admin/ceo/chat',headers=headers,json={'message':'새 사업 초안을 만들지 마세요. 질문에 답변만 하세요.'})
    assert response.status_code==200 and response.json()['jobs']==[]
    assert db.one('SELECT count(*) AS n FROM ventures')['n']==0


def test_approval_is_not_falsely_reported_as_a_new_product_launch(live):
    client,headers,db=live;seed_pending(db)
    response=client.post('/api/admin/ventures/venture_probe/decision',headers=headers,json={'approve':True})
    assert response.status_code==200 and not response.json()['released']
    assert '도구가 없으므로' not in response.json()['reply']
    assert '완료하지 않았습니다' in response.json()['reply']
    assert client.get('/api/store/info').json()['published'] is False


def test_broken_connected_model_never_creates_fallback_jobs(live,monkeypatch):
    client,headers,db=live
    import ai_provider
    monkeypatch.setattr(ai_provider,'status',AsyncMock(return_value={'mode':'hermes','name':'test','endpoint':''}))
    monkeypatch.setattr(ai_provider,'compose',AsyncMock(side_effect=ValueError('Invalid structured response')))
    before=db.one('SELECT count(*) AS n FROM jobs')['n']
    response=client.post('/api/admin/ceo/chat',headers=headers,json={'message':'마케팅 콘텐츠 업무를 검토해줘'})
    assert response.status_code==200 and response.json()['jobs']==[]
    assert '모델 응답 처리 실패' in response.json()['reply']
    assert '실행하지 않았습니다' in response.json()['reply']
    assert '모델이 연결되지' not in response.json()['reply']
    assert db.one('SELECT count(*) AS n FROM jobs')['n']==before


def test_new_idea_has_no_bundled_example_in_its_prompt(live,monkeypatch):
    client,headers,db=live
    import ai_provider,meeting_engine
    monkeypatch.setattr(ai_provider,'status',AsyncMock(return_value={'mode':'hermes','name':'test'}))
    plan={'name':'동네예약','problem':'빈 예약을 줄이기','market':'지역 서비스 사업자','product':'예약 취소 알림','price':19000,'validation':'고객 인터뷰','execution':'가설 검증'}
    mock=AsyncMock(return_value=json.dumps(plan,ensure_ascii=False))
    monkeypatch.setattr(ai_provider,'compose',mock)
    monkeypatch.setattr(meeting_engine,'run',AsyncMock())
    response=client.post('/api/admin/ceo/chat',headers=headers,json={'message':'월천만원 벌거리 의논좀해봐라'})
    assert response.status_code==200 and response.json()['venture']['proposal']['name']=='동네예약'
    context=json.loads(mock.call_args.args[1])
    assert context['previous_draft']['name']=='' and 'DealPage' not in json.dumps(context)
    assert db.one('SELECT count(*) AS n FROM ceo_meetings')['n']==1


def test_meeting_persists_each_real_call_before_next_speaker(live,monkeypatch):
    import asyncio,json,re
    import ai_provider,meeting_engine
    client,headers,db=live
    assert client.get('/api/admin/platform/workspace').status_code==401
    monkeypatch.setattr(ai_provider,'status',AsyncMock(return_value={'mode':'hermes','name':'test'}))
    mid=meeting_engine.start('수익 가설을 여러 관점에서 검토')
    calls=[]
    async def compose(system,user,max_tokens=1700):
        snapshot=client.get('/api/admin/platform/workspace',headers=headers).json()
        assert snapshot['meetings'][0]['status']=='running'
        assert len(snapshot['meetings'][0]['minutes'])==len(calls)
        calls.append(system)
        return '검증할 가설과 반론, 다음 단계를 실제 응답으로 기록합니다.'
    monkeypatch.setattr(ai_provider,'compose',compose)
    asyncio.run(meeting_engine.run(mid))
    row=meeting_engine._meeting_row(mid)
    assert row['status']=='completed' and len(row['minutes'])==5 and len(calls)==6
    assert [m['role'] for m in row['minutes']]==list(meeting_engine.DEFAULT_ROLES)
    assert row['summary']


def test_restart_marks_interrupted_meeting_without_deleting_minutes(live):
    client,headers,db=live
    import meeting_engine
    from platform_plugins.projects.project_zero_state import recover
    mid=meeting_engine.start('중단 회의의 기존 발언 보존 확인')
    meeting_engine._append(mid,{'role':'CPO','name':'제품 책임자','statement':'이미 저장한 발언'})
    recover(db,meeting_engine)
    row=meeting_engine._meeting_row(mid)
    assert row['status']=='failed' and len(row['minutes'])==1 and '재시작' in row['summary']


def test_partial_business_response_never_inherits_a_demo_product(live,monkeypatch):
    import asyncio,unittest
    import ai_provider,venture_engine
    client,headers,db=live
    monkeypatch.setattr(ai_provider,'status',AsyncMock(return_value={'mode':'hermes','name':'test'}))
    monkeypatch.setattr(ai_provider,'compose',AsyncMock(return_value='{"name":"추천 사업","price":19000}'))
    with unittest.TestCase().assertRaises(ValueError):asyncio.run(venture_engine.propose('새 사업 아이디어를 제안해줘'))
    assert db.one('SELECT count(*) AS n FROM ventures')['n']==0


def test_discussion_context_switch_is_explicit_and_locked_during_meeting(live):
    client,headers,db=live
    import ai_provider,meeting_engine
    system='현재 역할';user=json.dumps({'topic':'고객 검증','prior_colleagues':[]})
    assert ai_provider.platform_request_options(system,user)['context_scope']=='focused_discussion'
    url='/api/admin/platform/discussion-context'
    assert client.post(url,json={'include_engine_context':True}).status_code==401
    assert client.post(url,headers=headers,json={'include_engine_context':True}).status_code==200
    assert ai_provider.platform_request_options(system,user)['context_scope']=='native'
    assert client.get('/api/admin/platform/workspace',headers=headers).json()['include_engine_context'] is True
    meeting_engine.start('진행 중에는 설정이 바뀌지 않아야 합니다')
    assert client.post(url,headers=headers,json={'include_engine_context':False}).status_code==409


def plan_fixture():
    return {'summary':'추천안: 홈페이지 제작\n이유: 고객 검증\n산출물: 로컬 홈페이지와 검증 결과\n승인 범위: 로컬 제작만',
        'tasks':[{'phase':phase,'role':role,'title':title,'brief':title+'을 실제 수행','deliverable':title+' 문서/파일','acceptance':'실제 결과를 확인'} for phase,role,title in [
        ('requirements','CPO','요구사항 정리'),('design','CTO','구조 설계'),('implementation','CTO','홈페이지 제작'),('verification','QA','동작 검증')]]}


def test_meeting_plan_approval_is_atomic_and_dependencies_receive_results(live,monkeypatch):
    from platform_plugins.projects import project_zero_plans as plans
    import ai_provider,meeting_engine
    client,headers,db=live
    monkeypatch.setattr(ai_provider,'status',AsyncMock(return_value={'mode':'hermes'}))
    mid=meeting_engine.start('로컬 홈페이지를 만들 실행안 검토')
    summary,tasks=plans.parse(json.dumps(plan_fixture(),ensure_ascii=False))
    plans.save(db,mid,summary,tasks)
    url='/api/admin/platform/meeting-plans/'+mid+'/decision'
    assert db.one('SELECT count(*) AS n FROM jobs')['n']==0
    assert client.post(url,json={'approve':True}).status_code==401
    assert client.post(url,headers=headers,json={'approve':True}).status_code==409
    meeting_engine._finish(mid,'completed',summary)
    assert client.post(url,headers=headers,json={'approve':'true'}).status_code==409
    result=client.post(url,headers=headers,json={'approve':True})
    assert result.status_code==200 and len(result.json()['jobs'])==4
    assert client.post(url,headers=headers,json={'approve':True}).status_code==409
    ids=[j['id'] for j in result.json()['jobs']]
    assert [db.one('SELECT status FROM jobs WHERE id=?',(jid,))['status'] for jid in ids]==['queued','blocked','blocked','blocked']
    db.finish_job(ids[0],'요구사항 실제 산출물','llm');plans.advance(db)
    design=db.one('SELECT * FROM jobs WHERE id=?',(ids[1],))
    assert design['status']=='queued' and '요구사항 실제 산출물' in json.loads(design['arguments'])['brief']
    db.finish_job(ids[1],'설계 실패','llm','검증 실패');plans.advance(db)
    assert db.one('SELECT status FROM platform_meeting_plans WHERE meeting_id=?',(mid,))['status']=='failed'
    assert all(db.one('SELECT status FROM jobs WHERE id=?',(jid,))['status']=='failed' for jid in ids[2:])


def test_meeting_plan_success_handoff_and_rejection_never_starts_work(live):
    from platform_plugins.projects import project_zero_plans as plans
    import meeting_engine
    client,headers,db=live
    summary,tasks=plans.parse(json.dumps(plan_fixture(),ensure_ascii=False))
    mid=meeting_engine.start('기획 설계 제작 검증');plans.save(db,mid,summary,tasks);meeting_engine._finish(mid,'completed',summary)
    jobs=plans.decide(db,mid,True)['jobs']
    for index,job in enumerate(jobs):
        claimed=db.claim_job();assert claimed['id']==job['id']
        if index:assert '실제 산출물 0' in json.loads(claimed['arguments'])['brief']
        db.finish_job(job['id'],'실제 산출물 '+str(index),'llm')
    plans.advance(db)
    assert plans.latest(db)[0]['status']=='completed'
    mid2=meeting_engine.start('보류 검토');plans.save(db,mid2,summary,tasks);meeting_engine._finish(mid2,'completed',summary)
    before=db.one('SELECT count(*) AS n FROM jobs')['n'];plans.decide(db,mid2,False)
    assert db.one('SELECT count(*) AS n FROM jobs')['n']==before


def test_invalid_role_or_missing_build_verification_never_becomes_approvable(live):
    from platform_plugins.projects import project_zero_plans as plans
    import pytest
    value=plan_fixture();value['tasks'][0]['role']='CTO'
    with pytest.raises(ValueError):plans.parse(json.dumps(value))
    value=plan_fixture();value['tasks'].pop()
    with pytest.raises(ValueError):plans.parse(json.dumps(value))
    value=plan_fixture();value['tasks']=value['tasks'][2:]
    with pytest.raises(ValueError):plans.parse(json.dumps(value))


def test_real_meeting_synthesis_hook_reports_plan_without_auto_execution(live,monkeypatch):
    import asyncio,ai_provider,meeting_engine
    from platform_plugins.projects.project_zero_meeting import install
    from platform_plugins.projects import project_zero_plans as plans
    client,headers,db=live
    monkeypatch.setattr(ai_provider,'status',AsyncMock(return_value={'mode':'hermes'}))
    calls=[]
    async def compose(system,user,max_tokens=500):
        context=json.loads(user);calls.append(context)
        return json.dumps(plan_fixture(),ensure_ascii=False) if 'minutes' in context else '고객 요구와 검증할 가설입니다.'
    monkeypatch.setattr(ai_provider,'compose',compose)
    import server
    install(server.app)
    mid=meeting_engine.start('홈페이지 구축을 검토')
    asyncio.run(meeting_engine.run(mid))
    assert meeting_engine._meeting_row(mid)['status']=='completed'
    assert len(calls)==6 and len(plans.latest(db))==1
    assert plans.latest(db)[0]['report_message_id']
    assert plans.latest(db)[0]['status']=='pending'
    assert db.one('SELECT count(*) AS n FROM jobs')['n']==0
    assert db.one("SELECT body FROM ceo_messages WHERE speaker='ceo' ORDER BY rowid DESC LIMIT 1")['body'].endswith(plan_fixture()['summary'])


def test_existing_meeting_can_prepare_a_plan_without_repeating_specialists(live,monkeypatch):
    import ai_provider,meeting_engine,server,time
    from platform_plugins.projects.project_zero_meeting import install
    client,headers,db=live
    monkeypatch.setattr(ai_provider,'status',AsyncMock(return_value={'mode':'hermes'}))
    mock=AsyncMock(return_value=json.dumps(plan_fixture(),ensure_ascii=False))
    monkeypatch.setattr(ai_provider,'compose',mock);install(server.app)
    mid=meeting_engine.start('로컬 홈페이지 검토')
    meeting_engine._append(mid,{'role':'CPO','name':'제품','statement':'고객 가설을 검토'})
    meeting_engine._finish(mid,'completed','이전 요약')
    url='/api/admin/platform/meeting-plans/'+mid+'/prepare'
    assert client.post(url).status_code==401
    assert client.post(url,headers=headers).status_code==200
    for _ in range(50):
        if db.one('SELECT meeting_id FROM platform_meeting_plans WHERE meeting_id=?',(mid,)):break
        time.sleep(.01)
    assert client.post(url,headers=headers).status_code==409
    assert db.one('SELECT status FROM platform_meeting_plans WHERE meeting_id=?',(mid,))['status']=='pending'
    assert db.one('SELECT count(*) AS n FROM jobs')['n']==0
    mock.assert_awaited_once()


def test_cached_real_business_review_can_be_recovered_without_another_model_call(live,monkeypatch):
    import ai_provider,meeting_engine,time
    from platform_plugins.projects import project_zero_plans as plans
    client,headers,db=live
    monkeypatch.setattr(ai_provider,'status',AsyncMock(return_value={'mode':'hermes'}))
    mock=AsyncMock(side_effect=AssertionError('Cached recovery must not call model'))
    monkeypatch.setattr(ai_provider,'compose',mock)
    mid=meeting_engine.start('사업 검증 실험 설계')
    meeting_engine._finish(mid,'completed','기존 회의')
    value=plan_fixture();value['tasks']=[value['tasks'][0],value['tasks'][1],value['tasks'][3]]
    plans.cache_draft(db,mid,json.dumps(value,ensure_ascii=False))
    response=client.post('/api/admin/platform/meeting-plans/'+mid+'/prepare',headers=headers)
    assert response.status_code==200
    for _ in range(50):
        if db.one('SELECT meeting_id FROM platform_meeting_plans WHERE meeting_id=?',(mid,)):break
        time.sleep(.01)
    row=plans.latest(db)[0]
    assert row['status']=='pending' and row['report_message_id']
    assert db.one('SELECT count(*) AS n FROM jobs')['n']==0
    mock.assert_not_awaited()


def test_conversation_does_not_dispatch_unsolicited_model_tasks(live,monkeypatch):
    import ai_provider
    client,headers,db=live
    monkeypatch.setattr(ai_provider,'status',AsyncMock(return_value={'mode':'hermes'}))
    mock=AsyncMock(return_value=json.dumps({'intent':'conversation','reply':'제품·화면 흐름은 CPO, 기술 설계·구현은 CTO가 맡습니다.','tasks':[{'role':'CTO','action':'agent_task','title':'불필요한 검사','brief':'질문인데 실행하지 마세요'}]},ensure_ascii=False))
    monkeypatch.setattr(ai_provider,'compose',mock)
    result=client.post('/api/admin/ceo/chat',headers=headers,json={'message':'설계는 누가 하는 거야?'})
    assert result.status_code==200 and result.json()['jobs']==[]
    assert db.one('SELECT count(*) AS n FROM jobs')['n']==0
    system,user=mock.call_args.args
    assert 'intent="conversation"' in system and json.loads(user)['_platform_turn']=='dialogue'
    assert json.loads(user)['context_kind']=='role_reference'
    assert system.index('CEO')<system.index('CPO')
    assert 'CTO' in result.json()['reply']


def test_generated_example_poison_is_excluded_but_original_chat_is_preserved(live,monkeypatch):
    import ai_provider
    client,headers,db=live
    db.save_ceo_message('ceo','DealPage를 사용자의 사업으로 출시해야 합니다.')
    db.record_lesson('CEO','DealPage만 하면 됩니다','team_meeting',1)
    monkeypatch.setattr(ai_provider,'status',AsyncMock(return_value={'mode':'hermes'}))
    mock=AsyncMock(return_value='{"intent":"conversation","reply":"독립적인 홈페이지 방향부터 정하죠.","tasks":[]}')
    monkeypatch.setattr(ai_provider,'compose',mock)
    response=client.post('/api/admin/ceo/chat',headers=headers,json={'message':'새 홈페이지 방향에 대해 얘기하자'})
    assert response.status_code==200
    context=json.loads(mock.call_args.args[1]);assert 'DealPage' not in json.dumps(context)
    assert db.one("SELECT count(*) AS n FROM ceo_messages WHERE body LIKE '%DealPage%'")['n']==1


def test_role_personas_reach_real_meeting_and_employee_prompts(live,monkeypatch):
    import asyncio,ai_provider,meeting_engine,operations
    client,headers,db=live
    assert '화면 구성' in meeting_engine.TEAM['CPO']['priority']
    assert '아키텍처' in meeting_engine.TEAM['CTO']['priority']
    assert len({v['priority'] for v in meeting_engine.TEAM.values()})==7
    monkeypatch.setattr(ai_provider,'status',AsyncMock(return_value={'mode':'hermes'}))
    mock=AsyncMock(return_value='요구사항에 따라 아키텍처와 실제 구현 파일을 만들고 확인한 실행 결과를 보고합니다. 설계 문서에는 데이터와 API 및 화면 컴포넌트의 연결 관계를 적습니다.')
    monkeypatch.setattr(ai_provider,'compose',mock)
    asyncio.run(operations.agent_task({'role':'CTO','brief':'승인된 홈페이지 설계와 제작','owner_instruction':'홈페이지 제작'}))
    assert '아키텍처' in mock.call_args.args[0] and '구현' in mock.call_args.args[0]
    roles=client.get('/api/admin/platform/workspace',headers=headers).json()['team']['roles']
    assert any(r['role']=='CPO' and '화면 구성' in r['responsibility'] for r in roles)


def test_pending_draft_opinion_uses_app_context_without_native_project_memory(live):
    import ai_provider
    client,headers,db=live
    options=ai_provider.platform_request_options('한국어 AI CEO로서 소유자와 대화하세요.',json.dumps({'owner':'왜 이렇게 정했어?','draft':{'name':'새 홈페이지'}}))
    assert options['context_scope']=='focused_discussion'
    assert ai_provider.platform_request_options('CTO 업무',json.dumps({'owner_instruction':'설계해','task':'실제 설계 파일 작성'}))['context_scope']=='native'


def test_read_timeout_does_not_become_disconnected_or_spawn_rule_jobs(live,monkeypatch):
    import ai_provider,httpx
    client,headers,db=live
    monkeypatch.setattr(ai_provider,'status',AsyncMock(return_value={'mode':'configured','name':'fake'}))
    monkeypatch.setattr(ai_provider,'compose',AsyncMock(side_effect=httpx.ReadTimeout('injected timeout')))
    before=db.one('SELECT count(*) AS n FROM jobs')['n']
    response=client.post('/api/admin/ceo/chat',headers=headers,json={'message':'사업초안 1000만원월 벌만한거'})
    assert response.status_code==200 and response.json()['jobs']==[]
    assert '응답의 대기 시간이 초과' in response.json()['reply']
    assert '연결되지 않아' not in response.json()['reply']
    assert db.one('SELECT count(*) AS n FROM jobs')['n']==before


def test_model_timeout_job_is_failed_without_a_false_rules_execution_label(live,monkeypatch):
    import asyncio,operations,httpx
    client,headers,db=live
    async def fail(args):raise httpx.ReadTimeout('worker response timed out')
    monkeypatch.setitem(operations.ACTIONS,'agent_task',fail)
    jid=db.create_job('agent_task','CFO','응답 실패 검증',{'brief':'비용 초안'})
    asyncio.run(operations.process_one())
    row=db.one('SELECT * FROM jobs WHERE id=?',(jid,))
    assert row['status']=='failed' and row['mode']=='unconfirmed' and 'ReadTimeout' in row['error']


def test_native_worker_without_hermes_still_applies_profile_and_blocks_rules_fallback(live,tmp_path,monkeypatch):
    import base64,json,sys,time
    from unittest.mock import patch
    from pathlib import Path
    import server
    from platform_plugins.projects import runtime,store,python_packages
    client,headers,db=live
    source=Path(server.__file__).parent
    (source/'native_profile_probe.py').write_text("import asyncio,httpx,server,ai_provider\napp=server.app\nasync def status():return {'mode':'configured','name':'fake','endpoint':'http://127.0.0.1:1/v1'}\nasync def compose(system,user,max_tokens=1000):\n await asyncio.sleep(.4)\n raise httpx.ReadTimeout('native transport injection')\nai_provider.status=status\nai_provider.compose=compose\n",encoding='utf-8')
    packages=next(Path(item) for item in sys.path if str(item).replace('\\','/').endswith('.platform-runtime/python'))
    record={'id':'p_native_profile_test','repository':'hushmind3/project-zero','active_source':str(source),
            'adapter':{'kind':'fastapi','directory':'.','app':'native_profile_probe:app'},'harness':{'enabled':False},
            'environment':{'PROJECT_ZERO_DATA_DIR':str(tmp_path/'native-data')}}
    with patch.object(store,'STATE',tmp_path/'registry'),patch.object(python_packages,'folder',return_value=packages):
        store.save(record)
        try:
            api=runtime.invoke(record,{'path':'/openapi.json'})
            assert '/api/admin/platform/workspace' in json.loads(base64.b64decode(api['body']))['paths']
            response=runtime.invoke(record,{'path':'/api/admin/ceo/chat/submit','method':'POST','headers':{**headers,'content-type':'application/json'},'body':json.dumps({'message':'검색을해봐'})})
            assert response['status']==202
            deadline=time.monotonic()+5;protected=False;body=''
            while time.monotonic()<deadline:
                protected=protected or '원본 모델 응답 대기' in runtime.busy_reason()
                result=runtime.invoke(record,{'path':'/api/admin/platform/workspace','headers':headers})
                state=json.loads(base64.b64decode(result['body']))
                assert state['model_transport']=='native_api'
                if state['requests'] and state['requests'][-1]['status']!='working':
                    body=state['ceo']['messages'][-1]['body'];assert not state['jobs'];break
                time.sleep(.05)
            assert '응답의 대기 시간이 초과' in body and '연결되지 않아' not in body
            assert protected
            assert not runtime.WORKERS[record['id']].harness_pending
        finally:runtime.close()
