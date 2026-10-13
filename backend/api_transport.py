"""JSON rendering and forwarding for the existing single HTTP gateway."""
import math
from starlette.requests import Request
from fastapi.responses import JSONResponse


def finite_json(value):
    if isinstance(value,float) and not math.isfinite(value):return None
    if isinstance(value,dict):return {key:finite_json(item) for key,item in value.items()}
    if isinstance(value,(list,tuple)):return [finite_json(item) for item in value]
    return value


class FiniteJSONResponse(JSONResponse):
    def render(self,content):
        return super().render(finite_json(content))


class UnifiedAPI:
    async def __call__(self,scope,receive,send):
        route,forwarded,body=scope['state']['api_dispatch']
        received=False
        async def payload():
            nonlocal received
            if received:return await receive()
            received=True
            return {'type':'http.request','body':body,'more_body':False}
        await route.handle(forwarded,payload,send)


async def local_writes(request: Request, call_next):
    from api_context import JSONResponse
    from api_context import Request
    from api_context import app
    from api_context import apply_running
    from api_context import apply_state
    from api_context import json
    from api_context import system
    path=request.url.path;method=request.method
    if path=='/api':
        from urllib.parse import urlencode
        try:
            if method=='GET':
                operation=request.query_params.get('operation','');parameters=json.loads(request.query_params.get('payload','{}'))
            else:
                envelope=await request.json();operation=envelope.get('operation','');parameters=envelope.get('payload',{})
            if not isinstance(operation,str) or not operation or not isinstance(parameters,dict):raise ValueError('operation과 payload 객체를 전달하세요.')
            path='/api/'+operation;matched=None
            for internal_method in (('GET',) if method=='GET' else ('POST','GET')):
                forwarded={**request.scope,'path':path,'raw_path':path.encode('utf-8'),'method':internal_method,
                    'query_string':urlencode(parameters,doseq=True).encode() if internal_method=='GET' else b''}
                from menu_registry import dispatch
                matched=dispatch(forwarded,parameters)
                if matched:break
            if not matched:return JSONResponse({'detail':'등록되지 않은 백엔드 명령입니다.'},status_code=404)
            method=matched[1]['method'];body=json.dumps(parameters,ensure_ascii=False).encode('utf-8') if method=='POST' else b''
            matched[1]['headers']=[(key,value) for key,value in request.scope['headers'] if key.lower() not in (b'content-length',b'content-type')]+[(b'content-type',b'application/json'),(b'content-length',str(len(body)).encode())]
            request.state.api_dispatch=(*matched,body)
        except (ValueError,TypeError,AttributeError) as exc:return JSONResponse({'detail':str(exc)},status_code=400)
    elif path.startswith('/api/'):
        return JSONResponse({'detail':'단일 /api 통로를 사용하세요.'},status_code=404)
    origin = request.headers.get("origin")
    if method != "GET" and origin and origin not in {
        "http://127.0.0.1:5173", "http://localhost:5173",
        "http://127.0.0.1:8766", "http://localhost:8766"
    }:
        return JSONResponse({"detail": "로컬 화면에서 요청하세요."}, status_code=403)
    if method!='GET':
        allowed_stop=path in ('/api/stop','/api/system/stop','/api/system/prepare-restart','/api/library/stop') or path.startswith('/api/controls/') and parameters.get('enabled') is False
        if ((apply_running() and apply_state().get('target')!='frontend') or system.restarting) and not allowed_stop and path!='/api/system/apply':
            return JSONResponse({'detail':'변경 적용/서버 갱신 중입니다. 기존 작업은 보존합니다.'},status_code=409)
        conflict=path in ('/api/train','/api/stop','/api/settings','/api/checkpoints/restore','/api/system/stop') or path.startswith(('/api/controls/','/api/experts/','/api/provider/')) and path!='/api/provider/test' or path.startswith('/api/framework/') or path.startswith('/api/library/') and path not in ('/api/library/search','/api/library/inspect')
        if conflict:
            system.cancel()
    response=await call_next(request)
    if method!='GET':system.invalidate_states()
    return response


def react_index():
    from api_context import FRONTEND_DIST
    from api_context import FileResponse
    from api_context import HTTPException
    from api_context import app
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        raise HTTPException(503, "React 빌드가 없습니다. 서버켜기.cmd를 실행하세요.")
    return FileResponse(index, headers={"Cache-Control": "no-cache"})

