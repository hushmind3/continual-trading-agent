# 거래 운영

취합: `trading_menu_manager.py`. 이 파일만 상위 menu_registry가 import합니다.

- [운영 제어](control/README.md): control/
- [가상계좌 · 주문](paper_account/README.md): paper_account/

취합: submenu_manager.py → trading_menu_manager.py(대메뉴 등록) → 전체 menu_registry → API. 새 기능 구현은 소속 하위 폴더에 추가하고 소메뉴 매니저에 등록합니다.
