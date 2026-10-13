# 정책 학습

- 역할: menu.py: 메뉴 등록; handlers.py: 기존 API 처리. 
- 핵심 파일: handlers.py, menu.py, official_cli.py
- 상위 연결: ../submenu_manager.py → finance_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.

프론트 메뉴 주소: `#finance/policy_learning`; 화면: `frontend/src/pages/finance/finrl/policy_learning/PolicyLearning.tsx`. 백엔드 실행 모듈·API 작업명은 유지합니다.

수동 종목 선택 요청 필드를 제거했습니다. 새 정책은 해당 통화의 등록·가격 저장 종목을 사용합니다. 이어 학습은 선택된 저장 정책의 dataset.json, Champion 학습은 해당 Champion의 종목 구성으로 백엔드가 결정하고 기존 데이터·환경 검사를 적용합니다. 작업의 symbols와 CLI --symbols는 결정된 데이터셋을 실행 프로세스에 전달하는 내부 계약입니다. 학습·검사 실행은 미실행입니다.
