from fastapi import APIRouter
from ai_agent.Hermes.engine.http_adapter import invoke

router = APIRouter(prefix='/api/ai_agent/Hermes')

@router.get('/mcp/catalog')
def catalog(): return invoke('mcp/catalog')

@router.post('/mcp/catalog/install')
def install(request: dict): return invoke('mcp/catalog/install', request)

@router.get('/mcp')
def status(): return invoke('mcp')

@router.post('/mcp/save')
def save(request: dict): return invoke('mcp/save', request)

@router.post('/mcp/connect')
def connect(): return invoke('mcp/connect')
