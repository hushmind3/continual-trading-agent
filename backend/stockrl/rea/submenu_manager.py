"""REA menu coordinator."""
from .analysis.menu import MENU
from .project_browser.menu import MENU as PROJECTS
MENUS=(MENU,PROJECTS)

from .analysis.handlers import router as analysis_router
from .project_browser.handlers import router as project_browser_router
ROUTERS=(analysis_router,project_browser_router,)
