# 거래 운영

용도: 금융 거래 운영 소메뉴와 상위 등록 연결을 안내합니다.

취합: 이 폴더의 submenu_manager.ts → 상위 finance_menu_manager.ts → 모듈 register.ts → 플랫폼 자동 등록기입니다.

- [운영 제어](operation_control/README.md): operation_control/
- [가상계좌 · 주문](virtual_account_orders/README.md): virtual_account_orders/

취합: submenu_manager.ts → finance_menu_manager.ts(대메뉴 등록) → 전체 menu_registry → API. 새 기능 구현은 소속 하위 폴더에 추가하고 소메뉴 매니저에 등록합니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.
