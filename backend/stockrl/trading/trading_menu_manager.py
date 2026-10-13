"""거래 운영 아래 작은 메뉴만 연결합니다."""
from .trading_control_menu import MENU as CONTROL
from .paper_account_menu import MENU as PAPER

GROUP={"id":'trading',"title":'거래 운영',"menus":(CONTROL,PAPER,)}
