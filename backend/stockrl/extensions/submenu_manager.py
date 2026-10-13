"""프로젝트 확장 아래 작은 메뉴만 연결합니다."""
from stockrl.extensions.moe.menu import MENU as MOE
from stockrl.extensions.project_modules.menu import MENU as PROJECT_MODULES

MENUS=(MOE,PROJECT_MODULES,)

from .moe.handlers import router as moe_router
ROUTERS=(moe_router,)
