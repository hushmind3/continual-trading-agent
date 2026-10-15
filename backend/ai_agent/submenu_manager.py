"""Collect agent submenus without importing their execution engines."""
from ai_agent.Hermes.manager import MENU, router

MENUS = (MENU,)
ROUTERS = (router,)
