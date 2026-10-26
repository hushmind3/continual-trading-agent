from fastapi import APIRouter
from ai_agent.choki.engine.http_adapter import invoke

router = APIRouter(prefix='/api/ai_agent/choki')

@router.get('/autonomy')
def autonomy(id: str): return invoke('autonomy', {'id':id})

@router.get('/status')
def status(): return invoke('status')

@router.post('/engine/shutdown')
def shutdown_engine():
    from ai_agent.choki.engine.bridge import bridge
    from fastapi import HTTPException
    reason = bridge.busy_reason()
    if reason:
        raise HTTPException(409, reason)
    bridge.reserve_restart()
    try:
        bridge.close()
        return {'stopped': True}
    finally:
        bridge.cancel_restart()

@router.post('/chat')
def chat(request: dict):
    from ai_agent.choki.artifacts.handlers import uploaded_paths
    from fastapi import HTTPException
    try:request['attachments']=uploaded_paths(request.get('attachments',[]))
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc
    return invoke('chat', request)

@router.post('/chat/steer')
def steer(request: dict):
    from ai_agent.choki.artifacts.handlers import uploaded_paths
    from fastapi import HTTPException
    try:request['attachments']=uploaded_paths(request.get('attachments',[]))
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc
    return invoke('chat/steer', request)

@router.post('/stop')
def stop(): return invoke('stop')

@router.post('/answer')
def answer(request: dict): return invoke('answer', request)
