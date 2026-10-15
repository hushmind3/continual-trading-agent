from fastapi import APIRouter
from ai_agent.Hermes.engine.http_adapter import invoke

router = APIRouter(prefix='/api/ai_agent/Hermes')

@router.get('/status')
def status(): return invoke('status')

@router.post('/chat')
def chat(request: dict): return invoke('chat', request)

@router.post('/stop')
def stop(): return invoke('stop')

@router.post('/answer')
def answer(request: dict): return invoke('answer', request)
