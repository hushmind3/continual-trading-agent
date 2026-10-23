"""Collect Nazarick submenus before platform-wide API registration."""
from .overview.manager import MENU as overview_menu, router as overview
from .connections.manager import MENU as connections_menu, router as connections
from .activity.manager import MENU as activity_menu, router as activity

GROUP = {'menus': (overview_menu, connections_menu, activity_menu)}
ROUTERS = (overview, connections, activity)
