# 프로젝트 관리 화면 안내

React/Vite/Tailwind 공통 UI로 검색·설치·설치된 프로젝트·자동 작업 화면을 표시합니다. `Projects.tsx`는 단일 `/api`의 `projects/` 소메뉴를 사용합니다.

사용자 메뉴는 GitHub → 프로젝트 관리입니다. 설치된 앱의 등록은 공통 `frontend/src/shell/installed_navigation.ts`에서 GitHub → 앱별 중메뉴로 정규화합니다. 기존 설치본과 native 모듈도 적용하며 앱별 주소·컴포넌트·실행 기능은 보존합니다. Hermes의 MCP 소메뉴는 변경하지 않습니다.

- `RepositorySearch.tsx`: 설치 버튼·검색 30개/더 보기·정렬·한국어 설명 전환. 설치와 번역은 독립합니다.
- `InstalledProjects.tsx`: 분리(파일 보관), 재연결(저장본 재사용), 제거(프로젝트 파일·설정·기록 영구 삭제)를 구분합니다.
- `ProjectSettings.tsx`: 공통 Drawer를 즉시 열어 상태·환경 설정·로그를 표시합니다.
- `PackageTransfer.tsx`: 내보낸 앱 ZIP을 읽어 `projects/import`로 설치합니다. `InstalledProjects.tsx`의 내보내기는 `projects/export`가 만든 파일을 다운로드합니다. 사용자 데이터·환경 변수 값은 내보내지 않습니다. 금융·REA·Hermes 기본 항목에도 **독립 실행 소스** 버튼을 제공하며 기존 projects/export API를 재사용합니다. 이 ZIP은 전용 설치/실행 진입점을 포함하고 외부 앱 ZIP 가져오기와 형식이 다릅니다.
- 설치 후 앱을 열면 대기 중 이동 정보를 정리해 관리 화면으로 돌아갈 수 있습니다. 메뉴 적용 중 잠깐 API가 재연결돼도 다음 상태 조회에서 복구하며 설치 오류 메시지는 별도로 보존합니다.
- 분리/제거 후 `projects/installed.active_module_ids`에서 실제 API 모듈 해제를 확인하면 메뉴를 다시 읽습니다. 앱 행만 사라지고 기존 메뉴가 남는 상태로 완료하지 않습니다.
- 모델 자동 변환은 설치 화면/앱 설정의 스위치로 켜야 합니다. 설치 오류·번역 때문에 모델을 자동으로 불러오지 않습니다. 앱 의존성·내보낸 파일도 해당 앱 제거에 포함됩니다.
- `ProjectApp.tsx`: 원본 웹 UI 또는 유형별 공통 UI를 선택합니다. MCP는 `ProjectTask.tsx`가 자동으로 연결하고 대상·자연어 요청으로 Hermes 작업을 시작합니다. 세션을 선택해 대화로 이동합니다. 수동 `McpTools.tsx`는 개발자 상세에만 있습니다.
- `useKorean.ts`: 로컬 번역 캐시/진행 상태·원문 대체. 공통 UI는 `frontend/src/ui/`, 백엔드는 `../backend/manager.py`입니다.

확인: TypeScript·Vite와 상위 README의 실제 브라우저/에이전트 검사. 번역 불가·미지원 실행 유형을 설치 성공으로 숨기지 않습니다. 검사 결과와 미완료 사항은 상위 README에 적습니다.
