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
