"""REA menu coordinator."""
from rea.program_analysis.menu import MENU
from rea.project_explorer.menu import MENU as PROJECTS
MENUS=(MENU,PROJECTS)

from rea.program_analysis.handlers import router as program_analysis_router
from rea.project_explorer.handlers import router as project_explorer_router
ROUTERS=(program_analysis_router,project_explorer_router,)
