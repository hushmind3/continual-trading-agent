# 프로젝트 설치·관리

GitHub 검색·주소 등록 → 다운로드 → 구조 분석/어댑터 생성 → 의존성 설치 → 실행 확인 → 메뉴 연결을 담당합니다. `backend/manager.py`가 소메뉴 API와 실행 보호 훅을 등록합니다. 프론트는 `frontend/register.ts`에서 등록하며 공통 React/Vite/Tailwind UI를 사용합니다.

- `backend/github.py`: 공개 GitHub 검색·주소 검증·다운로드.
- `backend/adapters.py`: 기존 UI·FastAPI·Python 명령의 실행 규격 탐지 및 설치.
- `backend/installer.py`: 영속 설치 작업, 단계·실패 기록, 검증 후 모듈 게시.
- `backend/runtime.py`, `app_worker.py`: 공통 자원을 사용하는 앱 호출·원본 화면 제공. 메뉴별 HTTP 서버를 만들지 않습니다.
- `backend/handlers.py`: 단일 `/api`의 `projects/` 소메뉴 명령.
- `frontend/`: GitHub 검색, 주소 등록, 설치 내역과 원본 UI/공통 실행 화면.

소스·설치 기록·설정은 `runtime/projects/manage/`에 보존합니다. 생성된 `modules/external_*/`는 등록 어댑터이며 원본 소스나 사용자 데이터를 삭제하지 않습니다. 설치 버튼은 해당 저장소의 의존성 설치·빌드를 요청합니다. 실행 검증에 실패하면 사용 가능으로 표시하지 않습니다. 구조가 자동 탐지되지 않으면 설정된 Hermes에 어댑터 생성을 요청하고 생성 결과도 동일하게 검증합니다.

메뉴는 프로젝트 → 프로젝트 관리 → GitHub에서 추가/설치된 프로젝트입니다. 프론트 경로는 `#projects/manage/search`, `#projects/manage/installed`, API 소속은 `projects/manage`입니다. 설치가 끝나면 원본 프로젝트 이름의 대메뉴를 자동 생성합니다. 기존 금융·REA·Hermes도 실제 등록 정보로 목록에 표시하며, 이들을 외부 설치기로 변환한 것으로 표시하지 않습니다.

플랫폼 필수 기능은 이 프로젝트 안에 있습니다. Codex 개인 `.codex/skills` 폴더는 실행·설치·복구 의존성이 아닙니다. Python과 Node는 기존 실행기를 재사용합니다. Python 의존성을 추가할 때 이미 설치된 패키지 버전을 제약해 기존 금융·Hermes 환경의 임의 업그레이드를 막습니다. 충돌은 설치 실패로 표시하며 조용히 버전을 바꾸지 않습니다.

지원 어댑터는 정적 HTML, Vite 빌드, FastAPI ASGI, Python console script, 플랫폼 module.json입니다. 그 밖의 구조나 실행 실패는 준비된 Hermes에 실제 변환을 요청합니다. 모델이 없거나 승인 대기·변환 실패이면 바로 사용 가능으로 표시하지 않습니다. FastAPI는 원본 lifespan을 실행하는 별도 작업 프로세스에서 요청을 처리하며 HTTP 서버는 추가하지 않습니다. 원본 UI의 정적 파일만 `/assets/projects/`로 제공하고 기능 호출은 단일 `/api`를 사용합니다. fetch 기반 원본 UI 연결을 지원하며 WebSocket·스트리밍·바이너리 업로드와 모든 프레임워크를 포괄한다고 보장하지 않습니다.

업데이트는 새 소스에서 확인한 후 게시합니다. 실패하면 기존 어댑터·활성 소스를 유지하고 실패한 어댑터는 루트 휴지통에 보관합니다. 설치 중 취소, 단계·로그 확인, 환경 설정, 업데이트·분리를 제공합니다. 분리해도 원본 소스·설정·기록은 남고 재등록 시 저장된 어댑터 정보를 재사용합니다. 설치 리비전이 실제 호스트에 로드되기 전에는 사용 가능으로 표시하지 않습니다. 독립 배포 패키지 생성은 아직 별도 미완료 기능입니다.

공식 참조: [GitHub 검색](https://docs.github.com/en/rest/search/search), [npm ci](https://docs.npmjs.com/cli/v11/commands/npm-ci/).

## 실제 확인 — 2026-10-16

`development/scripts/verify_project_install.cjs`로 공개 `mdn/beginner-html-site-styled`를 실제 검색하고 화면의 등록 버튼을 눌렀습니다. 다운로드·구조 분석·Chromium 원본 화면 검사·생성 어댑터의 전체 import/TypeScript/빌드 확인·새 대메뉴 활성화·자동 이동·플랫폼 내 원본 UI 표시가 통과했습니다. 분리 API 실행 후 소스와 환경 설정 이름·설치 기록이 유지됐습니다. 검사 프로젝트는 분리 상태로 남기며 사용자 금융·REA·Hermes 데이터를 삭제하지 않았습니다. 원시 결과와 스크린샷은 Git 제외 `runtime/projects/manage/verification/github-install.json`, `installed-project.png`에 있습니다.

관련 Python 검사 24개가 통과했습니다. 실제 ASGI 작업 프로세스의 상태 유지와 작업 폴더, 원본 UI의 fetch→단일 API 연결, JavaScript 오류 시 설치 거부, 실패 업데이트의 기존 프로그램 복구, Windows 기록 잠금 재시도, 설치 리비전 적용 전 완료 표시 방지와 모듈 이름 충돌 거부를 포함합니다. 실제 `/assets/projects/<id>/` 마운트에서 원본 화면을 검사하며 잘못된 루트 자산 경로·빈 화면을 성공으로 표시하지 않습니다. 미지원 쿠키 인증은 어댑터가 필요하다고 거부하며 인증을 제거해 검사를 통과시키지 않습니다. 명령: `.venv/Scripts/python.exe -B -m unittest development.tests.test_project_installer development.tests.test_platform_modules development.tests.test_server_watchdog development.tests.test_hermes_execution -q`.

TypeScript·Vite 빌드와 서버 적용도 완료했습니다. AppWorkspace 공통 UI로 설치 앱의 중복 제목·큰 여백을 줄이고 원본 화면을 남은 높이에 표시합니다. Hermes에 추가한 요청별 workspace는 저장된 기본 설정을 덮어쓰지 않습니다.

미확인: 실제 Ornith 추론을 사용한 미지원 저장소의 자동 변환, 실제 외부 Vite/Python 패키지의 모든 의존성 조합, 다른 PC의 새 환경. 독립 배포 패키지 생성과 공통 프로젝트 협업 도구는 미완료입니다. 공개 정적 웹 프로젝트의 실사용 성공을 모든 GitHub 저장소의 성공으로 일반화하지 않습니다.
