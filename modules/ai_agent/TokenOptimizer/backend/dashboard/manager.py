from fastapi import APIRouter, HTTPException
from .data import snapshot

MENU = {'id': 'ai_agent/TokenOptimizer/dashboard', 'title': '대시보드',
        'operations': ['ai_agent/TokenOptimizer/'], 'views': [],
        'manager': 'ai_agent.TokenOptimizer.manager'}
router = APIRouter(prefix='/api/ai_agent/TokenOptimizer')

@router.get('/dashboard')
def dashboard(refresh: bool = False):
    try:
        return snapshot(refresh)
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(503, str(exc)) from exc
