# 정책 학습

- 역할: menu.py: 메뉴 등록; handlers.py: 기존 API 처리. 
- 핵심 파일: handlers.py, menu.py, official_cli.py
- 상위 연결: ../submenu_manager.py → finance_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.

프론트 메뉴 주소: `#finance/policy_learning`; 화면: `frontend/src/pages/finance/finrl/policy_learning/PolicyLearning.tsx`. 백엔드 실행 모듈·API 작업명은 유지합니다.

프론트는 KRW·USD 각각 등록된 학습 대상 종목 전체를 명시적으로 전달합니다. algorithms는 실제 선택한 SB3 클래스 생성자의 기본값을 추가로 반환하며 학습 정책을 생성하지 않습니다. 공식 설정·학습기·환경 규칙은 유지합니다.
