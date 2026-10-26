"""Hermes submenu: collect feature routers, do not implement an agent here."""
from fastapi import APIRouter
import asyncio
import logging
from ai_agent.choki.chat.handlers import router as chat
from ai_agent.choki.models.handlers import router as models
from ai_agent.choki.sessions.handlers import router as sessions
from ai_agent.choki.mcp.handlers import router as mcp
from ai_agent.choki.skills.handlers import router as skills
from ai_agent.choki.artifacts.handlers import router as artifacts
from ai_agent.choki.native.handlers import router as official
from ai_agent.choki.native.asgi import register_host
NATIVE_API_PREFIXES=('/api/ai_agent/choki/native/',)

# Run before serving any app/engine request; migration preserves and checks every row.
from ai_agent.choki.engine.locations import ROOT
from ai_agent.choki.chat.staff_migration import migrate
migrate(ROOT)

MENU = {'id': 'ai_agent/choki', 'title': 'choki', 'operations': ['ai_agent/choki/'],
        'views': [], 'frontend': 'frontend/src/pages/ai_agent/choki/Choki.tsx', 'manager': 'ai_agent.choki.manager'}
router = APIRouter()
for feature in (chat, models, sessions, mcp, skills, artifacts, official):
    router.include_router(feature)

_startup_task = None

@router.on_event('startup')
async def start_choki():
    """Boot the official scheduler/gateway independently of the first UI request."""
    global _startup_task
    async def start():
        from ai_agent.choki.engine.bridge import bridge
        try:
            await asyncio.to_thread(bridge.call,'official/http',{'path':'/api/status'},timeout=180)
        except Exception:
            logging.getLogger(__name__).exception('공식 헤르메스 자동 시작 실패; 설치·설정을 확인하세요.')
    _startup_task = asyncio.create_task(start(),name='choki-engine-start')


@router.on_event('shutdown')
def close_choki():
    from ai_agent.choki.engine.bridge import bridge
    bridge.close()


def busy_reason():
    from ai_agent.choki.engine.bridge import bridge
    return bridge.busy_reason()


def reserve_restart():
    from ai_agent.choki.engine.bridge import bridge
    return bridge.reserve_restart()


def cancel_restart():
    from ai_agent.choki.engine.bridge import bridge
    return bridge.cancel_restart()

close=close_choki
