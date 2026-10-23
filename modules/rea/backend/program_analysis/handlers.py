"""프로그램 분석 — existing API handlers."""
from __future__ import annotations
from fastapi import APIRouter
from rea.transport import FiniteJSONResponse
from fastapi import HTTPException
from zipfile import BadZipFile,LargeZipFile

router=APIRouter(default_response_class=FiniteJSONResponse)

@router.get('/api/rea/status')
def rea_status():
    from rea.program_analysis.extract import analysis_status
    return analysis_status()

@router.post('/api/rea/pick')
def rea_pick(request:dict):
    from rea.program_analysis.extract import pick
    try:return pick(request.get('kind','file'))
    except (OSError,ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc)) from exc


@router.post('/api/rea/analyze')
def rea_analyze(request:dict):
    from rea.program_analysis.extract import analyze
    try:return analyze(request.get('kind'),request.get('target'))
    except (BadZipFile,LargeZipFile) as exc:raise HTTPException(400,'손상되었거나 지원하지 않는 ZIP/APK/IPA 패키지입니다.') from exc
    except (OSError,ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc)) from exc


@router.post('/api/rea/stop')
def rea_stop():
    from rea.program_analysis.extract import stop
    stop();return {'message':'사용자가 REA 분석을 중지했습니다.'}



@router.on_event("shutdown")
def close_analysis():
    from rea.program_analysis.extract import stop
    stop()
