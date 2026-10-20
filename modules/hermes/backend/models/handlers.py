from fastapi import APIRouter
from ai_agent.Hermes.engine.http_adapter import invoke

router = APIRouter(prefix='/api/ai_agent/Hermes')

@router.get('/codex/status')
def codex_status(): return invoke('codex/status')

@router.post('/codex/login')
def codex_login(): return invoke('codex/login')

@router.post('/codex/models')
def codex_models(): return invoke('codex/models')

@router.get('/settings')
def settings(): return invoke('settings')

@router.post('/settings')
def save_settings(request: dict): return invoke('settings/save', request)

@router.post('/models')
def models(request: dict): return invoke('models', request)

@router.get('/models/local')
def local_models(): return invoke('models/local')

@router.post('/model/load')
def load(request: dict): return invoke('model/load', request)

@router.post('/model/unload')
def unload(): return invoke('model/unload')
