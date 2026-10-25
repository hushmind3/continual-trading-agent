"""Token optimization middle menu collects its dashboard submenu."""
from .dashboard import manager as dashboard

MENU = dashboard.MENU
router = dashboard.router
