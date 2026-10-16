# 프로젝트 관리 화면 안내

React/Vite/Tailwind 공통 UI로 검색·설치·설치된 프로젝트·자동 작업 화면을 표시합니다. `Projects.tsx`는 단일 `/api`의 `projects/` 소메뉴를 사용합니다.

- `RepositorySearch.tsx`: 설치 버튼·검색 30개/더 보기·정렬·한국어 설명 전환. 설치와 번역은 독립합니다.
- `InstalledProjects.tsx`: 분리(파일 보관), 재연결(저장본 재사용), 제거(프로젝트 파일·설정·기록 영구 삭제)를 구분합니다.
- `ProjectSettings.tsx`: 공통 Drawer를 즉시 열어 상태·환경 설정·로그를 표시합니다.
- `ProjectApp.tsx`: 원본 웹 UI 또는 유형별 공통 UI를 선택합니다. MCP는 `ProjectTask.tsx`가 자동으로 연결하고 대상·자연어 요청으로 Hermes 작업을 시작합니다. 세션을 선택해 대화로 이동합니다. 수동 `McpTools.tsx`는 개발자 상세에만 있습니다.
- `useKorean.ts`: 로컬 번역 캐시/진행 상태·원문 대체. 공통 UI는 `frontend/src/ui/`, 백엔드는 `../backend/manager.py`입니다.

확인: TypeScript·Vite와 상위 README의 실제 브라우저/에이전트 검사. 번역 불가·미지원 실행 유형을 설치 성공으로 숨기지 않습니다. 검사 결과와 미완료 사항은 상위 README에 적습니다.
