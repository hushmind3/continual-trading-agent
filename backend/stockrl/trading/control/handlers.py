"""운영 제어 — existing API handlers."""
from __future__ import annotations
from stockrl.api_context import APIRouter, BaseModel, FiniteJSONResponse, HTTPException, Literal, runtime, system

router=APIRouter(default_response_class=FiniteJSONResponse)

class ControlRequest(BaseModel):
    enabled:bool


@router.post("/api/controls/{name}")
def operation_control(name:Literal["feed","paper","engine","learning"],request:ControlRequest):
    try:return {"controls":runtime.command(name,request.enabled)}
    except (ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc))


@router.post('/api/system/start')
def start_system(values:dict):
    currencies=values.get('currencies',['USD','KRW'])
    if not currencies or not set(currencies)<= {'USD','KRW'}:raise HTTPException(400,'USD/KRW 운영 통화를 선택하세요.')
    try:return system.start(list(dict.fromkeys(currencies)))
    except ValueError as exc:raise HTTPException(409,str(exc))


@router.post('/api/system/stop')
def stop_system():
    return system.stop()

