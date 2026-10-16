# 프로젝트 관리 화면 안내

GitHub 주소 등록·검색·설치 상태와 설치된 앱 화면을 담당합니다. `Projects.tsx`가 단일 `/api`의 `projects/` 명령을 사용하며 `RepositorySearch.tsx`는 30개씩 검색·정렬·더 보기, `InstalledProjects.tsx`는 재시도·업데이트·분리를 제공합니다. `ProjectApp.tsx`는 원본 UI·Python 기능·`McpTools.tsx`의 실제 MCP 도구 화면을 선택합니다. 공통 UI는 `frontend/src/ui/`, 실행은 `../backend/manager.py`입니다.

설치 실패·취소·실행 연결 필요 항목에는 제거 버튼을 표시합니다. `projects/remove`가 활성 설치본 없는 항목의 소스·기록을 프로젝트 루트 휴지통에 상대 경로를 유지해 이동하고 목록에서 제거합니다. 활성 설치본이 있는 프로젝트의 분리는 기존 데이터 보존 동작을 유지합니다.

확인: 루트 `.venv/Scripts/python.exe -B -m unittest development.tests.test_project_installer -q`, `frontend/`에서 TypeScript와 Vite 빌드. 연결 필요는 설치 성공이 아니며, MCP 도구 연결 성공도 모든 외부 분석 엔진이 설치됐다는 뜻이 아닙니다. 실사용 결과는 상위 README에 기록합니다.
