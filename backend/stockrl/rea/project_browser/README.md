# 프로젝트 탐색

- 역할: menu.py: 메뉴 등록; handlers.py: 기존 API 처리. 
- 핵심 파일: handlers.py, menu.py, projects.py
- 상위 연결: ../submenu_manager.py → rea_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.

projects.py는 backend/rea_projects/의 물리적 저장 결과를 탐색합니다. 폴더명은 분석 대상 이름과 생성 시각입니다. 내부 프로젝트 ID와 원본/추론 구분을 유지하며 original/의 내용은 이름 변경 과정에서 수정하지 않습니다.
