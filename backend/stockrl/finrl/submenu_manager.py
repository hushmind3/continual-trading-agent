"""FinRL · 메인 아래 작은 메뉴만 연결합니다."""
from stockrl.finrl.policy_learning.menu import MENU as LEARNING
from stockrl.finrl.modules_tools.menu import MENU as MODULES_TOOLS

MENUS=(LEARNING,MODULES_TOOLS,)

from .policy_learning.handlers import router as policy_learning_router
ROUTERS=(policy_learning_router,)
