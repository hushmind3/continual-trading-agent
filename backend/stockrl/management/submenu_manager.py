"""연결 · 관리 아래 작은 메뉴만 연결합니다."""
from stockrl.management.connection_settings.menu import MENU as CONNECTION
from stockrl.management.diagnostics.menu import MENU as SYSTEM
from stockrl.management.backend_browser.menu import MENU as BACKEND_BROWSER

MENUS=(CONNECTION,SYSTEM,BACKEND_BROWSER)

from .connection_settings.handlers import router as connection_settings_router
from .diagnostics.handlers import router as diagnostics_router
from .backend_browser.handlers import router as backend_browser_router
ROUTERS=(connection_settings_router,diagnostics_router,backend_browser_router,)
