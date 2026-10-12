"""FinRL · 메인 아래 작은 메뉴만 연결합니다."""
from .policy_learning_menu import MENU as LEARNING
from .policy_evaluation_menu import MENU as PORTFOLIO
from .stock_data_menu import MENU as FINRL
from .stock_training_menu import MENU as STOCK_TRAINING
from .stock_backtest_menu import MENU as BACKTEST
from .finrl_tools_menu import MENU as FRAMEWORKS

GROUP={"id":'finrl',"title":'FinRL · 메인',"menus":(LEARNING,PORTFOLIO,FINRL,STOCK_TRAINING,BACKTEST,FRAMEWORKS,)}
