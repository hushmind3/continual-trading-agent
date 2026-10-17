"""거래 운영 아래 작은 메뉴만 연결합니다."""
from stockrl.trading.operation_control.menu import MENU as CONTROL
from stockrl.trading.virtual_account_orders.menu import MENU as PAPER

MENUS=(CONTROL,PAPER,)

from .operation_control.handlers import router as control_router
from .virtual_account_orders.handlers import router as paper_account_router
ROUTERS=(control_router,paper_account_router,)
