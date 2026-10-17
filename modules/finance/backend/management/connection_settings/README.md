# 연결 · 설정

- 역할: menu.py: 메뉴 등록; handlers.py: 기존 API 처리. 
- 핵심 파일: handlers.py, menu.py, provider_credentials.py
- 상위 연결: ../submenu_manager.py → finance_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.

프론트 메뉴 주소: `#finance/connection_settings`; 화면: `modules/finance/frontend/management/connection_settings/ConnectionSettings.tsx`. 백엔드 실행 모듈·API 작업명은 유지합니다.

거래소·브로커 인증은 키움만 등록합니다. Alpaca 연결 설정·직접 매매 도구와 Kraken 수집 코드를 제거했습니다. Yahoo·FMP·WRDS 시세·데이터 공급과 기존 인증 저장값·가격 자료는 유지합니다. FinRL 원본 초기화가 Alpaca SDK를 import하므로 내부 패키지 의존성과 키움 격리 환경은 유지합니다.

2026-10-14: 현재 연결 상태의 브로커 목록은 키움만 표시합니다. 설치된 공식 FinRL의 내부 SDK 의존성은 변경하지 않았습니다. 실제 state/connections API 응답을 확인했습니다.
