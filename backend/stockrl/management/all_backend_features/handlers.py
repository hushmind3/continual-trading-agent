"""백엔드 기능 전체 — existing API handlers."""
from __future__ import annotations
from api_context import APIRouter
from api_context import FileResponse
from api_context import FiniteJSONResponse
from api_context import HTTPException
from api_context import Literal
from api_context import RUNTIME
from api_context import re
from api_context import read_json
from api_context import system
from api_context import uuid

router=APIRouter(default_response_class=FiniteJSONResponse)

def framework_catalog():
    from stockrl.platform.framework_operations import catalog
    return catalog()


def framework_providers():
    from stockrl.finrl_trading.provider_settings.operations import provider_status
    return provider_status()


@router.post('/api/framework/providers/{provider}')
def framework_provider_save(provider:str,values:dict):
    from stockrl.management.connection_settings.handlers import provider
    from stockrl.finrl_trading.provider_settings.operations import save_provider
    try:return save_provider(provider,values)
    except (ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc))


@router.post('/api/framework/{action}')
def framework_task(action:str,parameters:dict):
    from stockrl.management.diagnostics_logs_code_apply.handlers import now
    from stockrl.platform.framework_operations import ACTIONS
    from stockrl.platform.framework_operations import validate_native_call
    if action not in ACTIONS:raise HTTPException(404,'등록된 공식 실행 기능이 아닙니다.')
    if action=='native_call':
        try:validate_native_call(parameters)
        except (ValueError,TypeError,KeyError) as exc:raise HTTPException(400,str(exc)) from exc
    with system.job_lock:
        if system.job_state()['running']:raise HTTPException(409,'현재 공식 작업 종료 후 실행하세요.')
        job_id=uuid.uuid4().hex
        job=system.start_job({'id':job_id,'command':'framework','action':action,'parameters':parameters,
            'currency':parameters.get('currency','USD'),'symbols':parameters.get('symbols',[]),'resume':False,
            'status':'starting','started_at':now(),'log':f'jobs/{job_id}.log','output':'framework-jobs/'+job_id})
    return {'message':ACTIONS[action][0]+' 실행을 시작했습니다.','job':job}


@router.get('/api/framework/result/{job_id}')
def framework_result(job_id:str,kind:Literal['json','csv']='json'):
    if not re.fullmatch('[0-9a-f]{32}',job_id):raise HTTPException(400,'작업 ID가 유효하지 않습니다.')
    path=RUNTIME/'framework-jobs'/job_id/('result.'+kind)
    if not path.is_file():raise HTTPException(404,'해당 작업의 결과 파일이 없습니다.')
    return FileResponse(path,filename=path.name)


@router.get('/api/framework/artifact/{job_id}/{filename:path}')
def framework_artifact(job_id:str,filename:str):
    if not re.fullmatch('[0-9a-f]{32}',job_id):raise HTTPException(400,'결과 경로가 유효하지 않습니다.')
    folder=(RUNTIME/'framework-jobs'/job_id).resolve();path=(folder/filename).resolve()
    recorded=read_json(folder/'result.json').get('files',[])
    if not path.is_relative_to(folder) or (filename not in recorded and not re.fullmatch(r'figure_[0-9]+\.png',filename)):raise HTTPException(400,'기록된 결과 파일만 열 수 있습니다.')
    if not path.is_file():raise HTTPException(404,'실제 생성된 그림 파일이 없습니다.')
    return FileResponse(path)

