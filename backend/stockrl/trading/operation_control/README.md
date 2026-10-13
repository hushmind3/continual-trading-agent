# 운영 제어

- 역할: menu.py: 메뉴 등록; handlers.py: 기존 API 처리. 
- 핵심 파일: handlers.py, menu.py, operations_runtime.py, operations_settings.py
- 상위 연결: ../submenu_manager.py → finance_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.

프론트 메뉴 주소: `#finance/operation_control`; 화면: `frontend/src/pages/finance/trading/operation_control/OperationControl.tsx`. 백엔드 폴더·import 이름은 프론트 소메뉴 폴더와 일치합니다. API 작업명은 유지합니다.

Expert 모델 설정 경로는 operations_settings.settings().model_dir 및 registry_file에서 제공합니다. 실제 등록·선택 정보는 바탕화면 모델/experts/expert_registry.json과 각 모델 폴더의 expert.json에 있습니다. 프로젝트 configs/experts.json을 읽지 않습니다.
