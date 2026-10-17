"""Collect all finance submenus without changing their implementations."""
from .trading.submenu_manager import MENUS as TRADING,ROUTERS as TRADING_ROUTERS
from .finrl.submenu_manager import MENUS as FINRL,ROUTERS as FINRL_ROUTERS
from .extensions.submenu_manager import MENUS as EXTENSIONS,ROUTERS as EXTENSIONS_ROUTERS
from .management.submenu_manager import MENUS as MANAGEMENT,ROUTERS as MANAGEMENT_ROUTERS

MENUS=(*TRADING,*FINRL,*EXTENSIONS,*MANAGEMENT)
ROUTERS=(*TRADING_ROUTERS,*FINRL_ROUTERS,*EXTENSIONS_ROUTERS,*MANAGEMENT_ROUTERS)
