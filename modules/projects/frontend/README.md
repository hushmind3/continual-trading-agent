# 프로젝트 관리 화면 안내

React/Vite/Tailwind 공통 UI로 검색·설치·설치된 프로젝트·자동 작업 화면을 표시합니다. `Projects.tsx`는 단일 `/api`의 `projects/` 소메뉴를 사용합니다.

사용자 메뉴는 GitHub → 프로젝트 관리입니다. 설치된 앱의 등록은 공통 `frontend/src/shell/installed_navigation.ts`에서 GitHub → 앱별 중메뉴로 정규화합니다. 기존 설치본과 native 모듈도 적용하며 앱별 주소·컴포넌트·실행 기능은 보존합니다. Hermes의 MCP 소메뉴는 변경하지 않습니다.

- `RepositorySearch.tsx`: 설치 버튼·검색 30개/더 보기·정렬·한국어 설명 전환. 설치와 번역은 독립합니다.
- `InstalledProjects.tsx`·`ProjectCard.tsx`: 설치 앱/기본 앱 목록, 실제 확인 표시와 분리/재연결/제거를 구분합니다. 분리는 독립 폴더를 자동 준비하는 비동기 작업이며 메뉴 해제 대기도 표시합니다.
- `ProjectSettings.tsx`: 공통 Drawer에 실제 설치 위치·확인 기록을 표시합니다. 환경 변수는 선택 사항으로 접고 로그/전달용 ZIP은 개발자 상세로 옮깁니다.
- `PackageTransfer.tsx`: 내보낸 앱 ZIP을 읽어 `projects/import`로 설치합니다. `InstalledProjects.tsx`의 내보내기는 `projects/export`가 만든 파일을 다운로드합니다. 사용자 데이터·환경 변수 값은 내보내지 않습니다. 금융·REA·Hermes도 기본 분리/재연결을 제공하며 전달용 ZIP은 설치 정보의 개발자 상세에서 기존 projects/export API를 재사용합니다. 이 ZIP은 전용 설치/실행 진입점을 포함하고 외부 앱 ZIP 가져오기와 형식이 다릅니다.
- 설치 후 앱을 열면 대기 중 이동 정보를 정리해 관리 화면으로 돌아갈 수 있습니다. 메뉴 적용 중 잠깐 API가 재연결돼도 다음 상태 조회에서 복구하며 설치 오류 메시지는 별도로 보존합니다.
- 분리/제거 후 `projects/installed.active_module_ids`에서 실제 API 모듈 해제를 확인하면 메뉴를 다시 읽습니다. 앱 행만 사라지고 기존 메뉴가 남는 상태로 완료하지 않습니다.
- 모델 자동 변환은 설치 화면/앱 설정의 스위치로 켜야 합니다. 설치 오류·번역 때문에 모델을 자동으로 불러오지 않습니다. 앱 의존성·내보낸 파일도 해당 앱 제거에 포함됩니다.
- `ProjectApp.tsx`: 원본 웹 UI 또는 유형별 공통 UI를 선택합니다. MCP는 `ProjectTask.tsx`가 자동으로 연결하고 대상·자연어 요청으로 Hermes 작업을 시작합니다. 세션을 선택해 대화로 이동합니다. 수동 `McpTools.tsx`는 개발자 상세에만 있습니다.
- `useKorean.ts`: 로컬 번역 캐시/진행 상태·원문 대체. 공통 UI는 `frontend/src/ui/`, 백엔드는 `../backend/manager.py`입니다.

확인: TypeScript·Vite와 상위 README의 실제 브라우저/에이전트 검사. 번역 불가·미지원 실행 유형을 설치 성공으로 숨기지 않습니다. 검사 결과와 미완료 사항은 상위 README에 적습니다.

Projects.tsx는 폴더 열기·잔재 정리와 비동기 분리 상태를 관리합니다. 주 동작은 실행/분리/다시 연결이며 ZIP 다운로드가 분리의 필수 단계가 아닙니다. 기본 앱도 같은 목록에서 분리합니다. 화면의 main 영역은 공통 Shell이 소유하고 이 기능은 section으로 렌더링합니다. 한국어 자동 번역은 명시적 선택 때만 활성화해 화면 열기만으로 로컬 추론을 요청하지 않습니다.

InstallerApp.tsx·ScriptParameter.tsx: powershell 원본 설치기의 필수 경로·Windows 폴더 선택·선택 값·스위치를 공통 Input/Select/Button/Panel로 자동 표시합니다. ProjectApp.tsx가 유형에 따라 선택하며 설치 진행·중지·결과를 제공합니다. ProjectCard의 설치 화면 준비됨은 실제 프로그램 설치 완료를 뜻하지 않습니다. 원본 UI가 있는 앱은 기존 AppFrame을 계속 사용합니다.

InstallerApp은 프로젝트 관리의 앱별 폴더와 자동 설치 위치를 표시합니다. managed 설치 대상은 사용자 입력에서 제외하며 기존 프로그램을 읽는 경로만 선택하도록 구분합니다. 설치 정보의 폴더 열기도 특정 버전 source 대신 앱 소유 부모를 엽니다.

CliApp.tsx·GeneratedFieldInput.tsx: 원본 메타데이터를 받아 선택/숫자/스위치/목록/필수 입력과 결과 화면을 공통 컴포넌트로 구성합니다. 앱별 React 구현은 만들지 않습니다. ProjectApp은 원본 웹 UI를 유지하며 Python CLI는 자동 기능 화면, Windows 설치기와 함께 발견한 Python 도구는 프로젝트 기능 탭으로 연결합니다. 기존 원시 CLI 실행은 자동 추출 실패 시 고급 기능으로 유지합니다.

현재 상태(2026-10-19): Project Zero 전용 화면·실행 보정·검사기는 폐기했습니다. 재설치한 앱은 일반 설치 경로로 원본 UI/API를 사용하며 저장소 이름에 따른 전용 처리를 적용하지 않습니다. 공통 설치·실행·선택형 Hermes 연결은 유지합니다.
