# FinRL 모듈 · 도구

- 역할: menu.py: 메뉴 등록. 공통 모듈 목록은 단일 state의 framework 뷰에서 제공하며 공통 실행은 management/backend_browser에 연결됩니다. 
- 핵심 파일: menu.py
- 상위 연결: ../submenu_manager.py → finance_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.

프론트 메뉴 주소: `#finance/finrl_modules_tools`; 화면: `frontend/src/pages/finance/finrl/finrl_modules_tools/FinrlModulesTools.tsx`. 백엔드 실행 모듈·API 작업명은 유지합니다.
