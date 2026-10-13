"""FinRL · 메인 아래 작은 메뉴만 연결합니다."""
from .policy_learning_menu import MENU as LEARNING
from .finrl_tools_menu import MENU as FRAMEWORKS

GROUP={"id":'finrl',"title":'FinRL · 메인',"menus":(LEARNING,FRAMEWORKS,)}
