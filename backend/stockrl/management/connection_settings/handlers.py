"""연결 · 설정 — existing API handlers."""
from __future__ import annotations
from api_context import APIRouter
from api_context import BaseModel
from api_context import FiniteJSONResponse
from api_context import HTTPException
from api_context import Literal
from stockrl.finrl.price_data.operations import collection_status
from api_context import runtime
from api_context import system

router=APIRouter(default_response_class=FiniteJSONResponse)

def connections():
    from stockrl.management.diagnostics_logs_code_apply.handlers import capabilities
    info=collection_status()
    return {"api":{"status":"connected"},"data":info,"brokers":[
        {"name":name,"status":capabilities()[key]["status"],"reason":capabilities()[key]["reason"]}
        for name,key in (("키움","kiwoom"),("Alpaca","alpaca"))]}


class CredentialRequest(BaseModel):
    environment:Literal["paper","real"]="real"
    app_key:str=""
    secret:str=""
    account:str=""


def provider():
    from stockrl.management.connection_settings.provider_credentials import public_status
    from stockrl.trading.operation_control.operations_settings import settings
    return public_status(settings().state_dir)


@router.post("/api/provider/connect")
def connect_provider(request:CredentialRequest):
    from stockrl.management.connection_settings.provider_credentials import connect_credentials
    from stockrl.trading.operation_control.operations_settings import settings
    if runtime.controls['feed']:raise HTTPException(409,'기존 시세 수신을 중지한 뒤 공급원 인증을 변경하세요.')
    try:return connect_credentials(settings().state_dir,request.environment,request.app_key,request.secret,request.account)
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(400,str(exc))


@router.post("/api/provider/test")
def check_provider(request:CredentialRequest):
    from stockrl.management.connection_settings.provider_credentials import test_connection
    from stockrl.trading.operation_control.operations_settings import settings
    try:return test_connection(settings().state_dir,"kiwoom",request.environment)
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(400,str(exc))


@router.post("/api/provider/public")
def public_feed():
    if runtime.controls['feed']:raise HTTPException(409,'시세 수신을 중지한 뒤 공급원을 변경하세요.')
    from stockrl.management.connection_settings.provider_credentials import _write_settings
    from stockrl.management.connection_settings.provider_credentials import read_settings
    from stockrl.trading.operation_control.operations_settings import settings
    root=settings().state_dir;value=read_settings(root);value['provider']='yahoo'
    _write_settings(root,value)
    return {"message":"기존 공개 시세 공급원을 선택했습니다."}


@router.post('/api/provider/disconnect')
def disconnect_provider():
    runtime.command('feed',False)
    return {'message':'시세 연결 중지를 요청했습니다. 저장된 인증 정보는 유지합니다.'}


def operational_settings():
    from stockrl.finrl.policy_learning.handlers import source_settings
    from stockrl.trading.operation_control.operations_settings import settings
    current=settings()
    return {"risk":vars(current.risk),"data":vars(current.data),"symbols":current.symbols,
            "expert_devices":current.resources.expert_devices,"sac_readonly":source_settings()}


@router.post("/api/settings")
def save_operational_settings(values:dict):
    from stockrl.trading.operation_control.operations_settings import update
    if set(values)-{"risk","data","symbols","expert_devices"}:raise HTTPException(400,"운영 설정만 변경할 수 있습니다. SAC 설정은 원본값을 사용합니다.")
    if runtime.controls['feed']:raise HTTPException(409,"시세 수신을 멈춘 뒤 운영 설정을 변경하세요.")
    try:value=update(values)
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc
    if runtime.account:
        from stockrl.trading.operation_control.operations_settings import settings
        current=settings();runtime.account.fee=current.risk.fee;runtime.account.slippage=current.risk.slippage
    if system.expert_pool:
        system.expert_pool.settings.resources.expert_devices=value.get('expert_devices',{})
    return {"settings":value}

