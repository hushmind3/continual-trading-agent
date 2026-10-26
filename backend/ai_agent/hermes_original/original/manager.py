"""Platform lifecycle API; original application routes remain original-owned."""
from fastapi import APIRouter
from .. import runtime

MENU = {'id': 'ai_agent/HermesOriginal', 'title': '헤르메스 원본',
        'operations': ['ai_agent/HermesOriginal/'], 'views': [],
        'manager': 'ai_agent.hermes_original.manager'}
router = APIRouter(prefix='/api/ai_agent/HermesOriginal')


@router.get('/status')
def status():
    return runtime.status()


@router.post('/start')
def start():
    return runtime.start()


@router.post('/stop')
def stop():
    return runtime.stop()
