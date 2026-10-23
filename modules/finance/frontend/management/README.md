# 연결 · 관리

취합: `finance_menu_manager.ts`. 이 파일만 상위 menu_registry가 import합니다.

- [연결 · 설정](connection_settings/README.md): connection_settings/

취합: submenu_manager.ts → finance_menu_manager.ts(대메뉴 등록) → 전체 menu_registry → API. 새 기능 구현은 소속 하위 폴더에 추가하고 소메뉴 매니저에 등록합니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.


사용자 메뉴는 연결·설정만 등록합니다. 진단·코드 적용 및 전체 백엔드 카탈로그는 사용자 메뉴에서 제외합니다. 공통 기능 실행에 사용하는 내부 모듈은 유지합니다.
