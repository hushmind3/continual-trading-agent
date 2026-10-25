"""Hermes submenu: collect feature routers, do not implement an agent here."""
from fastapi import APIRouter
from ai_agent.Hermes.chat.handlers import router as chat
from ai_agent.Hermes.models.handlers import router as models
from ai_agent.Hermes.sessions.handlers import router as sessions
from ai_agent.Hermes.mcp.handlers import router as mcp
from ai_agent.Hermes.skills.handlers import router as skills
from ai_agent.Hermes.artifacts.handlers import router as artifacts
from ai_agent.Hermes.native.handlers import router as official
from ai_agent.Hermes.native.asgi import register_host
NATIVE_API_PREFIXES=('/api/ai_agent/Hermes/native/',)

# Run before serving any app/engine request; migration preserves and checks every row.
from ai_agent.Hermes.engine.locations import ROOT
from ai_agent.Hermes.chat.staff_migration import migrate
migrate(ROOT)

MENU = {'id': 'ai_agent/Hermes', 'title': '헤르메스', 'operations': ['ai_agent/Hermes/'],
        'views': [], 'frontend': 'modules/hermes/frontend/Hermes.tsx', 'manager': 'ai_agent.Hermes.manager'}
router = APIRouter()
for feature in (chat, models, sessions, mcp, skills, artifacts, official):
    router.include_router(feature)


@router.on_event('shutdown')
def close_hermes():
    from ai_agent.Hermes.engine.bridge import bridge
    bridge.close()


def busy_reason():
    from ai_agent.Hermes.engine.bridge import bridge
    return bridge.busy_reason()


def reserve_restart():
    from ai_agent.Hermes.engine.bridge import bridge
    return bridge.reserve_restart()


def cancel_restart():
    from ai_agent.Hermes.engine.bridge import bridge
    return bridge.cancel_restart()

close=close_hermes
