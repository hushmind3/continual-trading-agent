# FinRL · 메인

취합: `finrl_menu_manager.py`. 이 파일만 상위 menu_registry가 import합니다.

- [정책 학습](policy_learning/README.md): policy_learning/
- [FinRL 모듈 · 도구](tools/README.md): tools/

취합: submenu_manager.py → finrl_menu_manager.py(대메뉴 등록) → 전체 menu_registry → API. 새 기능 구현은 소속 하위 폴더에 추가하고 소메뉴 매니저에 등록합니다.
