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
    assert '모델 계획 생성 실패' in response.json()['reply']
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
