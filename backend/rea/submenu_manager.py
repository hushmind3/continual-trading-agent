"""REA menu coordinator."""
from rea.analysis.menu import MENU
from rea.project_browser.menu import MENU as PROJECTS
MENUS=(MENU,PROJECTS)

from rea.analysis.handlers import router as analysis_router
from rea.project_browser.handlers import router as project_browser_router
ROUTERS=(analysis_router,project_browser_router,)
