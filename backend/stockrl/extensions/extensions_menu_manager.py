"""프로젝트 확장 아래 작은 메뉴만 연결합니다."""
from .moe_menu import MENU as MOE
from .project_modules_menu import MENU as PROJECT_MODULES

GROUP={"id":'extensions',"title":'프로젝트 확장',"menus":(MOE,PROJECT_MODULES,)}
