from fastapi import APIRouter
from ai_agent.Hermes.engine.http_adapter import invoke

router = APIRouter(prefix='/api/ai_agent/Hermes')

@router.get('/skills')
def skills(): return invoke('skills')

@router.get('/skill')
def skill(name: str): return invoke('skill', {'name': name})
