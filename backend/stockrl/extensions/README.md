# 프로젝트 확장

취합: `extensions_menu_manager.py`. 이 파일만 상위 menu_registry가 import합니다.

- [MoE](moe/README.md): moe/
- [프로젝트 모듈](project_modules/README.md): project_modules/

취합: submenu_manager.py → extensions_menu_manager.py(대메뉴 등록) → 전체 menu_registry → API. 새 기능 구현은 소속 하위 폴더에 추가하고 소메뉴 매니저에 등록합니다.
