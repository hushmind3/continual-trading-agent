"""Platform lifecycle API; OpenClaw owns its dashboard and agent routes."""
from fastapi import APIRouter
from . import runtime

MENU = {'id': 'ai_agent/OpenClawOriginal', 'title': 'OpenClaw 원본',
        'operations': ['ai_agent/OpenClawOriginal/'], 'views': [],
        'manager': 'ai_agent.OpenClawOriginal.manager'}
router = APIRouter(prefix='/api/ai_agent/OpenClawOriginal')


@router.get('/status')
def status():
    return runtime.status()


@router.post('/start')
def start():
    return runtime.start()


@router.post('/stop')
def stop():
    return runtime.stop()
