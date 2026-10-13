# MoE

- 역할: menu.py: 메뉴 등록; handlers.py: 기존 API 처리. 
- 핵심 파일: handlers.py, menu.py
- 상위 연결: ../submenu_manager.py → finance_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.

프론트 메뉴 주소: `#finance/moe`; 화면: `frontend/src/pages/finance/extensions/moe/Moe.tsx`. 백엔드 실행 모듈·API 작업명은 유지합니다.

Expert 조회의 기준 폴더는 operations_settings.settings().model_dir(바탕화면 모델/experts)입니다. Champion 모델 폴더와 구분합니다. 화면 조회에서 PT 내용 읽기·가중치/정밀도 자동 검사는 수행하지 않습니다. 등록 JSON과 경로·파일 메타데이터만 표시하며, 미확인 정밀도는 실행 실패로 단정하지 않습니다. 모델 파일 목록도 같은 Expert 기준으로 등록 여부를 판별합니다.
