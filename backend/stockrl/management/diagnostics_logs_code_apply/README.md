# 진단 · 로그 · 코드 적용

- 역할: menu.py: 메뉴 등록; handlers.py: 기존 API 처리. 
- 핵심 파일: handlers.py, menu.py
- 상위 연결: ../submenu_manager.py → finance_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.

프론트 메뉴 주소: `#finance/diagnostics_logs_code_apply`; 화면: `frontend/src/pages/finance/management/diagnostics_logs_code_apply/DiagnosticsLogsCodeApply.tsx`. 백엔드 폴더·import 이름은 프론트 소메뉴 폴더와 일치합니다. API 작업명은 유지합니다.

모델 목록의 상태 서명은 전체 rglob 대신 등록 인덱스·모델 설명 JSON·등록 가중치의 직접 파일 상태만 확인합니다. 초기 파일 목록 생성과 사용자의 명시적 갱신은 기존 검색기를 사용합니다. 미등록 하위 파일의 추가는 목록 갱신으로 확인합니다. 재시작 보호는 Hermes도 포함하며 상태 확인 실패를 무시하지 않습니다.
