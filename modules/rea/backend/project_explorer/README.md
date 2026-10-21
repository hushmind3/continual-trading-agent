# 프로젝트 탐색

- 역할: menu.py: 메뉴 등록; handlers.py: 기존 API 처리. 
- 핵심 파일: handlers.py, menu.py, projects.py
- 상위 연결: ../submenu_manager.py → rea_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 기존 기록 조회 확인. 실제 폴더 열기 GUI 확인은 별도입니다.

projects.py는 runtime/rea/project_explorer/projects/의 물리적 저장 결과를 탐색합니다. 폴더명은 분석 대상 이름과 생성 시각입니다. 내부 프로젝트 ID와 원본/추론 구분을 유지하며 original/의 내용은 이름 변경 과정에서 수정하지 않습니다.

- saved_projects/: 분석 대상별 실제 파일 저장 폴더 (Git 제외).
- 프론트 연결: #rea/project_explorer → rea/projects·rea/project/tree,file,open → projects.py.
- 분석 저장: analysis/extract.py가 projects.py의 OUTPUT을 공유합니다. 원본 파일과 추론 결과는 계속 분리합니다.

2026-10-14: 잘못되거나 불완전한 project.json은 전체 목록을 중단시키지 않습니다. 임시 저장 실패·불완전 기록·원문 파일 탐색 회귀 검사 통과.

런타임: `runtime/rea/project_explorer/projects/`. 기존 저장 프로젝트를 이동하고 project.json의 폴더 참조도 갱신합니다. 추출된 original 파일은 수정하지 않습니다.

Mac의 rea/project/open은 공유 platform_native.open_folder로 Finder를 사용합니다. Windows startfile은 Windows에서만 호출합니다. 기존 프로젝트 경계·기록·실제 저장 경로는 유지하며 새 폴더나 별도 탐색 서버를 만들지 않습니다. 2026-10-22 기존 저장 기록 조회는 확인했고 Finder 창을 열어 확인하지는 않았습니다.
