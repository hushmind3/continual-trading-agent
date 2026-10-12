# 메뉴별 수정 위치

먼저 해당 큰 메뉴 README를 읽습니다. 작은 메뉴 연결 파일은 해당 화면의 API·상태·프론트 경로를 기록합니다.

| 큰 메뉴 | 큰 메뉴 연결 파일 | 작은 메뉴 수 |
| --- | --- | --- |
| 거래 운영 | trading/trading_menu_manager.py | 3 |
| FinRL 메인 | finrl/finrl_menu_manager.py | 6 |
| FinRL-Trading 보조 | finrl_trading/finrl_trading_menu_manager.py | 1 |
| 프로젝트 확장 | extensions/extensions_menu_manager.py | 2 |
| 연결·관리 | management/management_menu_manager.py | 2 |

화면 수정은 각 작은 메뉴에 기록된 프론트 파일에서 진행합니다. 공통 상태나 모델 캐시의 변경이 필요하지 않으면 SystemOperations를 수정하지 않습니다.
