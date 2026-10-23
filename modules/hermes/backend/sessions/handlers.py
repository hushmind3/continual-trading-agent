from fastapi import APIRouter
from ai_agent.Hermes.engine.http_adapter import invoke

router = APIRouter(prefix='/api/ai_agent/Hermes')

@router.get('/sessions')
def sessions(): return invoke('sessions')

@router.post('/session/create')
def create(request: dict): return invoke('session/create', request)

@router.get('/session')
def session(id: str): return invoke('session', {'id': id})

@router.post('/session/archive')
def archive(request: dict): return invoke('session/archive', request)

@router.post('/session/rename')
def rename(request: dict): return invoke('session/rename', request)
