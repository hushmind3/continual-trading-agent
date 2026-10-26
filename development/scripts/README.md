# Execution and setup

- start_server.py: 기존 소유 서버에 변경된 소스를 적용하고 단일 API 응답을 확인합니다. 플랫폼 서버가 메뉴별 런타임을 일괄 시작하는 오래된 `system/start` 호출은 사용하지 않습니다.
- Git 제외 설치 모듈도 등록 서명으로 변경을 추적해 프론트와 API를 함께 갱신합니다. 감시기가 빌드만 하고 API를 유지해 새 메뉴 활성화가 대기하던 경로를 수정했습니다. 실행 중 작업 보호는 그대로 적용합니다.
- verify_project_detachment.cjs: 실제 공개 GitHub 정적 앱의 설치·브라우저·자동 분리·단독 실행·재연결·완전 제거와 모바일 화면을 확인합니다. 검사 앱만 제거하고 모델은 사용하지 않습니다.
- server_watchdog.py: 실행 창과 분리된 단일 감시 프로세스. 서버 종료 시 기존 실행기로 API만 복구합니다.
- verify_module_detach.py: 실제 Hermes 폴더를 잠시 분리·복원하고 자동 등록·프론트 빌드·API 복원·설정 보존·중앙 코드 무변경을 확인합니다. 실행 중 작업은 먼저 확인하며 실패해도 폴더를 복원합니다. 결과는 `runtime/platform/module-verification.json`입니다.
- verify_module_registration.py: 새로운 대메뉴·API·React 화면을 가진 검사 모듈을 폴더 하나로 추가·분리합니다. 기존 메뉴·API 보존과 중앙 파일 수정 0건을 확인하며 검사 모듈은 runtime/platform에 보관합니다.
- verify_project_portability.cjs: 모델을 사용하지 않고 화면에서 앱 ZIP 내보내기 → 파일 설치 → 원본 UI → 제거/소유 파일 삭제를 확인합니다. 검사 전용 앱만 만들고 성공·실패 모두 정리하며 기록은 `runtime/projects/manage/verification/`에 둡니다.
- install_windows.py: 최소 호스트와 각 모듈의 전용 Python/Node 패키지를 설치합니다. 없는 모듈은 건너뜁니다.
- requirements/: 호스트 명세와 개발 검사 패키지, 금융 소유 명세를 연결하는 호환 파일입니다.


사용자 검사: 루트에서 `.venv\Scripts\python.exe -m unittest discover -s development/tests`, frontend 폴더에서 `npm run typecheck`, `npm run test:api`, `npm run test:browser`. 요청 없는 자동 검사·백그라운드 검사는 실행하지 않습니다.

npm은 루트 workspace 설치를 사용합니다. 루트 workspace는 플랫폼 frontend만 포함합니다. 검사 명령은 루트 npm run typecheck/test:api/test:browser로도 실행할 수 있습니다.

모듈 참조 조사: .venv\Scripts\python.exe -B development/scripts\audit_module_usage.py. AST·import 경로만 읽어 운영 참조·검사 전용·참조 없음 후보를 출력합니다. 플랫폼 코드 import·함수 실행·삭제는 수행하지 않습니다.

서버켜기.cmd는 서버·현재 프론트만 적용하고 화면을 엽니다. 전체 시스템 시작(system/start), 시세·추론·학습·매매 및 자동 진단은 호출하지 않습니다. Git/Node는 이미 설치된 실행 파일을 사용하며 추가 설치하지 않습니다.

서버 실행 후 자동 복구 감시기를 함께 유지합니다. 정상 상태는 5초마다 가벼운 health API만 확인하며, 서버가 응답하지 않아도 포트에 실행 중인 프로세스가 있으면 강제 종료하지 않습니다. 포트가 비었을 때만 시작 잠금을 확보해 서버를 복구합니다. 중복 실행은 파일 잠금으로 방지하며 실패 시 60초 간격으로 재시도합니다. 소스 적용 중에는 같은 시작 잠금으로 대기합니다. 복구는 기존 프론트 빌드를 사용하며 금융 자동운영·학습·에이전트 작업은 재개하지 않습니다.

감시 상태·오류는 Git 제외 경로 `runtime/platform/server-watchdog.json`, 실행 로그는 `server-watchdog.log`에 남깁니다. 수동으로 서버를 완전히 끄려면 먼저 `runtime/platform/server-watchdog.stop` 빈 파일을 만들고 상태가 stopped인지 확인한 뒤 서버를 종료합니다. `서버켜기.cmd`를 다시 실행하면 감시를 재개합니다. PC 종료·절전 중에는 동작하지 않으며 Windows 로그인 자동 시작은 등록하지 않습니다.

2026-10-16 확인: 복구 관련 단위 검사 4개 통과. 실행 중 작업이 없는 API 프로세스를 종료한 뒤 새 PID로 복구되고 health가 정상인 것을 확인했습니다. 감시기 재시작 요청 시 기존 PID가 유지되어 중복 실행되지 않았습니다. PC 재부팅 후 자동 시작과 운영체제가 감시기까지 종료하는 상황은 확인하지 않았습니다.

런타임 경로 통일: 서버·감시·적용 기록은 `runtime/platform/`입니다. `runtime_layout.py`는 중지된 기존 런타임의 메뉴별 이동·제어 JSON 경로 갱신을 담당합니다. 전체 소속 표는 backend/README.md를 참조하세요.

런타임 이관은 대상 충돌을 먼저 확인하고 경로 이동 후 실제 제어 JSON만 갱신합니다. 복사된 모델 소스·추출된 original 트리는 검색하지 않습니다. 경로 참조 갱신은 한도 내 제어 파일에 한정하며 원본 모델·토크나이저를 검사하지 않습니다.

모듈의 실행 중 작업은 등록된 busy_reason 훅을 통해 공통 재시작 차단 목록에 포함합니다. 모듈 폴더·등록 정보 변경 시 import 사전 확인, 프론트 빌드, 서버 적용을 자동 처리합니다. 작업 중이거나 차단 상태를 확인할 수 없으면 적용을 보류합니다. 프론트 독립 적용은 기존 작업을 중지하지 않습니다.

환경 분리: `module_sources.py`는 설치기가 플랫폼 공통 도구를 Python 환경에 연결합니다. `install_windows.py`는 `.venv/platform/`과 Choki 공식 설치기를 준비하고, Choki의 Python·Node 런타임은 공식 Hermes PM이 `runtime/ai_agent/choki/installs/`와 `runtime/shared/engines/hermes-pm/`에서 관리합니다.



현재 등록 동기화: health의 module_signature는 실행 서버가 로드한 등록 상태입니다. 감시기는 이 값과 디스크·적용된 프론트/백엔드 등록 서명을 함께 비교합니다. 빠른 분리/재연결/제거로 이전 디스크 상태로 돌아와도 메뉴/API 잔재를 다시 적용합니다. 설치 완료는 두 빌드 등록의 적용까지 기다립니다. 관련 감시 회귀 검사 7개 통과.

verify_windows_installer.cjs: 기존 pluto-re의 원본 Windows 설치기 자동 탐지와 한국어 옵션 UI를 확인합니다. 원본 스크립트를 빈 검사 경로에서 호출해 필수 게임 누락 오류가 화면에 나오는지만 확인하고 다운로드·사용자 게임 변경은 하지 않습니다. 브라우저 오류·390px 가로 넘침을 검사하고 검사 경로/실행 상태는 정리합니다. 실제 게임 설치는 사용자 게임 경로가 필요합니다.

verify_automatic_ui.cjs: UI/설명 파일 없는 일반 Python CLI 검사 소스에서 실행 유형을 자동 추출해 앱 파일 설치 경로를 실행하고 2개 명령의 생성 UI·원본 실행/결과 파일·등록 코드만 존재함·모바일 화면을 확인합니다. 별도 앱 UI를 만들거나 사용자 모델/GitHub 다운로드를 사용하지 않습니다. 성공/준비 실패 모두 소유 임시 폴더 경계를 확인해 정리합니다. 결과 runtime/projects/manage/verification/automatic-ui.json입니다.

공식 원본 소스는 루트 `.gitmodules`의 고정 버전으로 복원합니다. 주력 헤르메스는 `backend/ai_agent/choki/engine/upstream` 전체 소스와 `engine/setup.py`의 공식 PM·잠금된 npm 워크스페이스·TUI 빌드를 사용합니다. CI 프론트 의존성도 공식 package-lock의 web 워크스페이스로 준비합니다. 공식 패키지 실제 경로를 해석하므로 web/node_modules 고정 배치에 의존하지 않습니다. 신규 설치기는 소스가 없을 때만 해당 서브모듈을 준비하고 구형 모듈 .venv·browser 설치는 호출하지 않습니다. 원본 앱은 업데이트·참고용 별도 홈을 유지합니다. 플랫폼 설치와 원본 앱의 PM/Node 패키지 준비는 별도이며, 현재 설치본을 정리할 때 다시 설치하지 않습니다. [Hermes 원본](../../backend/ai_agent/hermes_original/README.md), [OpenClaw 원본](../../backend/ai_agent/openclaw_original/README.md)의 실제 설치·업데이트 경로를 따릅니다.

## macOS 실행

Python은 bin/python, 서버 잠금은 fcntl, 포트 소유권은 lsof로 확인합니다. 서버/감시기는 터미널과 분리해 유지합니다. 호스트는 APIRoute 직접 등록과 호환되는 FastAPI 0.115.14를 사용합니다. 새 버전의 지연 include_router가 메뉴를 누락시키므로 호스트 요구사항에서 버전을 고정했습니다. 실제 실행 결과와 남은 범위는 루트 README를 봅니다.

Mac 설치 분기는 CUDA·키움 전용 설치를 건너뛰고, environment(gpu=True)를 직접 호출해도 macOS에서는 명시적으로 거절합니다. Mac 진입 .command 두 파일은 실행 권한을 Git에도 보존합니다.

Mac 설치·내보내기 정리(2026-10-22): install_windows.py는 이름과 무관하게 기존 OS 분기를 사용하며 npm은 공통 npm_command의 Node+실제 npm-cli.js 인수로 실행합니다. module_sources의 같은 .pth hook이 모듈 소스와 공유 native 도구를 연결합니다. 기존 환경에는 hook만 갱신했고 패키지 재설치·추가 다운로드는 수행하지 않았습니다. CUDA·키움은 Mac 설치 대상에서 제외합니다. 독립 기본 모듈의 Mac 설치도 같은 설치기를 재사용하며 Metal 실행기는 설치된 Homebrew llama-server에 연결합니다.

GitHub Actions는 공식 Hermes package.json의 engines.node에서 Node 버전을 읽습니다. backend-integrity는 실제 사용 SDK·Torch CPU·기존 Playwright 환경을 준비하며 Windows 설치기 실행은 windows-installer 작업으로 분리합니다. 테스트 fixture는 현재 직원 고유 ID·모듈 소유 경로·공식 제공자 resolver 계약을 따릅니다. 로컬 검사는 GitHub 통과 판정으로 대신하지 않습니다.



명령 소속 검사는 모든 업무 명령의 실제 메뉴 소속과 공통 호스트의 정확한 6개 제어 명령을 구분해 검증합니다. system 소속의 임의 명령을 허용하거나 화면 메뉴를 추가하지 않습니다.
