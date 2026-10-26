from fastapi import APIRouter
from ai_agent.choki.engine.http_adapter import invoke

router = APIRouter(prefix='/api/ai_agent/choki')

@router.post('/skill/toggle')
def toggle(request: dict): return invoke('skill/toggle', request)

@router.get('/skill/content')
def content(name: str): return invoke('skill/content', {'name':name})

@router.post('/skill/save')
def save(request: dict): return invoke('skill/save', request)

@router.get('/skills')
def skills(): return invoke('skills')

@router.get('/skill')
def skill(name: str): return invoke('skill', {'name': name})
