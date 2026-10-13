# 거래 운영

취합: `finance_menu_manager.py`. 이 파일만 상위 menu_registry가 import합니다.

- [운영 제어](control/README.md): control/
- [가상계좌 · 주문](paper_account/README.md): paper_account/

취합: submenu_manager.py → finance_menu_manager.py(대메뉴 등록) → 전체 menu_registry → API. 새 기능 구현은 소속 하위 폴더에 추가하고 소메뉴 매니저에 등록합니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.
