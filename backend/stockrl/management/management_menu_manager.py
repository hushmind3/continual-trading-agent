"""연결 · 관리 아래 작은 메뉴만 연결합니다."""
from .connection_settings_menu import MENU as CONNECTION
from .diagnostics_menu import MENU as SYSTEM

GROUP={"id":'management',"title":'연결 · 관리',"menus":(CONNECTION,SYSTEM,)}
