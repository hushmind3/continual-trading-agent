"""Use the real CEO synthesis call to propose an approval-gated, role-specific plan."""
from contextvars import ContextVar
import asyncio
import functools
import json
from fastapi import Header,HTTPException

CURRENT=ContextVar('project_zero_meeting',default='')
PREPARING=set()
TASKS=set()

def install(app):
    import ai_provider,meeting_engine as meetings,database as db,server
    if __package__:
        from . import project_zero_plans as plans
    else:
        import project_zero_plans as plans
    original_run=meetings.run;original_compose=ai_provider.compose;claim=db.claim_job
    @functools.wraps(original_run)
    async def run(mid,*args,**kwargs):
        token=CURRENT.set(mid)
        try:
            result=await original_run(mid,*args,**kwargs)
            row=meetings._meeting_row(mid)
            if row and row['status']=='completed':
                report=db.one('SELECT id FROM ceo_messages WHERE body=? ORDER BY rowid DESC LIMIT 1',('[팀 회의 완료] '+row['summary'],))
                if report:plans.attach_report(db,mid,report['id'])
            return result
        finally:CURRENT.reset(token)
    @functools.wraps(original_compose)
    async def compose(system,user,max_tokens=2048):
        try:context=json.loads(user)
        except (ValueError,TypeError):context={}
        mid=CURRENT.get()
        if not mid or not isinstance(context,dict) or not {'topic','minutes'}<=context.keys():
            return await original_compose(system,user,max_tokens=max_tokens)
        system=('당신은 CEO입니다. 현재 회의만 종합해 승인할 실행안을 만드세요. JSON 객체만 반환하세요. '
            'summary는 한국어 4줄 이내, 추천안·이유·산출물·승인 범위를 요약합니다. 직원 발언을 나열하지 마세요. '
            'tasks는 1~8개로 각 phase,role,title,brief,deliverable,acceptance가 필수입니다. '
            'phase requirements=CPO(고객 문제·요구사항), design=CTO(설계), implementation=CTO(실제 제작), '
            'verification=QA(검증), research=CMO/CFO/CS(시장·비용·고객 조사)입니다. '
            '제작할 때는 기획→설계→제작→QA 검증 순서가 필수입니다. 단순 검토면 필요한 조사만 제안하세요. '
            '선행 결과가 다음 담당자에게 전달됩니다. 아직 실행하지 않았으며 승인 전 업무는 생성하지 않습니다. '
            '사용자가 지정하지 않은 기존 플랫폼 프로젝트나 제품을 주제로 선택하지 마세요. 직원 발언의 확인되지 않은 제품명·기존 프로젝트 추정을 채택하지 마세요. '
            '지출·외부 공개·메일 발송은 별도 승인이 필요합니다. '
            '형식: {"summary":"추천안...","tasks":[{"phase":"research","role":"CMO","title":"...","brief":"...","deliverable":"...","acceptance":"..."}]}')
        raw=await original_compose(system,user,max_tokens=2200)
        summary,tasks=plans.parse(raw)
        plans.save(db,mid,summary,tasks)
        return summary
    def claim_job():
        plans.advance(db)
        return claim()
    meetings.run=run;ai_provider.compose=compose;db.claim_job=claim_job
    @app.post('/api/admin/platform/meeting-plans/{mid}/prepare')
    async def prepare(mid:str,x_project_zero_token:str|None=Header(None)):
        server.require_admin(x_project_zero_token)
        row=meetings._meeting_row(mid)
        if not row or row['status']!='completed':raise HTTPException(409,'완료된 회의가 필요합니다.')
        if mid in PREPARING or db.one('SELECT meeting_id FROM platform_meeting_plans WHERE meeting_id=?',(mid,)):
            raise HTTPException(409,'이미 실행안을 작성 중이거나 작성했습니다.')
        if (await ai_provider.status()).get('mode')=='rules':raise HTTPException(409,'실제 모델을 연결하세요.')
        # Recheck after the awaited provider status before owning the preparation.
        if mid in PREPARING:raise HTTPException(409,'이미 작성 중입니다.')
        PREPARING.add(mid)
        async def work():
            token=CURRENT.set(mid)
            try:
                summary=await ai_provider.compose('CEO 회의 종합',json.dumps({'topic':row['topic'],'minutes':row['minutes']},ensure_ascii=False),max_tokens=2200)
                message_id=db.save_ceo_message('ceo','[팀 회의 완료] '+summary)
                plans.attach_report(db,mid,message_id)
            except Exception as exc:
                db.save_ceo_message('ceo','실행안을 작성하지 못했습니다. 업무는 실행하지 않았습니다. '+str(exc)[:240])
            finally:CURRENT.reset(token);PREPARING.discard(mid)
        task=asyncio.create_task(work());TASKS.add(task);task.add_done_callback(TASKS.discard)
        return {'preparing':True,'meeting_id':mid}

    @app.post('/api/admin/platform/meeting-plans/{mid}/decision')
    async def decision(mid:str,body:dict,x_project_zero_token:str|None=Header(None)):
        server.require_admin(x_project_zero_token)
        if body.get('approve') is True and (await ai_provider.status()).get('mode')=='rules':raise HTTPException(409,'실제 모델을 연결한 뒤 승인하세요.')
        try:return plans.decide(db,mid,body.get('approve'))
        except ValueError as exc:raise HTTPException(409,str(exc)) from exc
