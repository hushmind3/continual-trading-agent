"""Hermes submenu: collect feature routers, do not implement an agent here."""
from fastapi import APIRouter
from ai_agent.Hermes.chat.handlers import router as chat
from ai_agent.Hermes.models.handlers import router as models
from ai_agent.Hermes.sessions.handlers import router as sessions
from ai_agent.Hermes.mcp.handlers import router as mcp
from ai_agent.Hermes.skills.handlers import router as skills

MENU = {'id': 'ai_agent/Hermes', 'title': 'Hermes', 'operations': ['ai_agent/Hermes/'],
        'views': [], 'frontend': 'pages/ai_agent/Hermes/Hermes.tsx', 'manager': 'ai_agent.Hermes.manager'}
router = APIRouter()
for feature in (chat, models, sessions, mcp, skills):
    router.include_router(feature)


@router.on_event('shutdown')
def close_hermes():
    from ai_agent.Hermes.engine.bridge import bridge
    bridge.close()
