"""프로그램 분석 — existing API handlers."""
from __future__ import annotations
from stockrl.api_context import APIRouter, FiniteJSONResponse, HTTPException

router=APIRouter(default_response_class=FiniteJSONResponse)

@router.post('/api/rea/pick')
def rea_pick(request:dict):
    from stockrl.rea.analysis.extract import pick
    try:return pick(request.get('kind','file'))
    except (OSError,ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc)) from exc


@router.post('/api/rea/analyze')
def rea_analyze(request:dict):
    from stockrl.rea.analysis.extract import analyze
    try:return analyze(request.get('kind'),request.get('target'))
    except (OSError,ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc)) from exc


@router.post('/api/rea/stop')
def rea_stop():
    from stockrl.management.diagnostics.handlers import stop
    from stockrl.rea.analysis.extract import stop
    stop();return {'message':'사용자가 REA 분석을 중지했습니다.'}

