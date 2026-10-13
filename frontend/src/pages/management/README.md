# 연결 · 관리

취합: `management_menu_manager.ts`. 이 파일만 상위 menu_registry가 import합니다.

- [연결 · 설정](connection_settings/README.md): connection_settings/
- [진단 · 로그 · 코드 적용](diagnostics/README.md): diagnostics/
- [백엔드 기능 전체](backend_browser/README.md): backend_browser/

취합: submenu_manager.ts → management_menu_manager.ts(대메뉴 등록) → 전체 menu_registry → API. 새 기능 구현은 소속 하위 폴더에 추가하고 소메뉴 매니저에 등록합니다.
