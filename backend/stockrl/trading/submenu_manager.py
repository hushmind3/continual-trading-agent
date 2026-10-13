"""거래 운영 아래 작은 메뉴만 연결합니다."""
from stockrl.trading.control.menu import MENU as CONTROL
from stockrl.trading.paper_account.menu import MENU as PAPER

MENUS=(CONTROL,PAPER,)

from .control.handlers import router as control_router
from .paper_account.handlers import router as paper_account_router
ROUTERS=(control_router,paper_account_router,)
