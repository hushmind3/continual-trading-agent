# Execution and setup

- start_server.py: 기존 소유 서버에 소스를 적용하고 단일 API를 실행합니다.
- Git 제외 설치 모듈도 등록 서명으로 변경을 추적해 프론트와 API를 함께 갱신합니다. 감시기가 빌드만 하고 API를 유지해 새 메뉴 활성화가 대기하던 경로를 수정했습니다. 실행 중 작업 보호는 그대로 적용합니다.
- server_watchdog.py: 실행 창과 분리된 단일 감시 프로세스. 서버 종료 시 기존 실행기로 API만 복구합니다.
- verify_module_detach.py: 실제 Hermes 폴더를 잠시 분리·복원하고 자동 등록·프론트 빌드·API 복원·설정 보존·중앙 코드 무변경을 확인합니다. 실행 중 작업은 먼저 확인하며 실패해도 폴더를 복원합니다. 결과는 `runtime/platform/module-verification.json`입니다.
- verify_module_registration.py: 새로운 대메뉴·API·React 화면을 가진 검사 모듈을 폴더 하나로 추가·분리합니다. 기존 메뉴·API 보존과 중앙 파일 수정 0건을 확인하며 검사 모듈은 runtime/platform에 보관합니다.
- verify_project_portability.cjs: 모델을 사용하지 않고 화면에서 앱 ZIP 내보내기 → 파일 설치 → 원본 UI → 제거/소유 파일 삭제를 확인합니다. 검사 전용 앱만 만들고 성공·실패 모두 정리하며 기록은 `runtime/projects/manage/verification/`에 둡니다.
- install_windows.py: 기존 주 환경·키움·REA 설치 진입점입니다.
- requirements/: 기존 의존성과 고정 버전 명세. 파일 내용·버전은 변경하지 않았습니다.

루트 `서버켜기.cmd`·`설치.cmd`에서 호출합니다. `.venv/`·`.venv/kiwoom/` 경로는 유지합니다. FinRL-X 외부 원본과 설치 연결은 제거했습니다. 금융 데이터 코드는 backend/stockrl/finrl/price_data/와 provider_settings/에 있습니다.

사용자 검사: 루트에서 `.venv\Scripts\python.exe -m unittest discover -s development/tests`, frontend 폴더에서 `npm run typecheck`, `npm run test:api`, `npm run test:browser`. 요청 없는 자동 검사·백그라운드 검사는 실행하지 않습니다.

npm은 루트 workspace 설치를 사용합니다. REA install()은 루트 npm ci로 프론트와 REA의 고정 버전을 함께 설치합니다. 검사 명령은 루트 npm run typecheck/test:api/test:browser로도 실행할 수 있습니다.

모듈 참조 조사: .venv\Scripts\python.exe -B development/scripts\audit_module_usage.py. AST·import 경로만 읽어 운영 참조·검사 전용·참조 없음 후보를 출력합니다. 플랫폼 코드 import·함수 실행·삭제는 수행하지 않습니다.

서버켜기.cmd는 서버·현재 프론트만 적용하고 화면을 엽니다. 전체 시스템 시작(system/start), 시세·추론·학습·매매 및 자동 진단은 호출하지 않습니다. Git/Node는 이미 설치된 실행 파일을 사용하며 추가 설치하지 않습니다.

서버 실행 후 자동 복구 감시기를 함께 유지합니다. 정상 상태는 5초마다 가벼운 health API만 확인하며, 서버가 응답하지 않아도 포트에 실행 중인 프로세스가 있으면 강제 종료하지 않습니다. 포트가 비었을 때만 시작 잠금을 확보해 서버를 복구합니다. 중복 실행은 파일 잠금으로 방지하며 실패 시 60초 간격으로 재시도합니다. 소스 적용 중에는 같은 시작 잠금으로 대기합니다. 복구는 기존 프론트 빌드를 사용하며 금융 자동운영·학습·에이전트 작업은 재개하지 않습니다.

감시 상태·오류는 Git 제외 경로 `runtime/platform/server-watchdog.json`, 실행 로그는 `server-watchdog.log`에 남깁니다. 수동으로 서버를 완전히 끄려면 먼저 `runtime/platform/server-watchdog.stop` 빈 파일을 만들고 상태가 stopped인지 확인한 뒤 서버를 종료합니다. `서버켜기.cmd`를 다시 실행하면 감시를 재개합니다. PC 종료·절전 중에는 동작하지 않으며 Windows 로그인 자동 시작은 등록하지 않습니다.

2026-10-16 확인: 복구 관련 단위 검사 4개 통과. 실행 중 작업이 없는 API 프로세스를 종료한 뒤 새 PID로 복구되고 health가 정상인 것을 확인했습니다. 감시기 재시작 요청 시 기존 PID가 유지되어 중복 실행되지 않았습니다. PC 재부팅 후 자동 시작과 운영체제가 감시기까지 종료하는 상황은 확인하지 않았습니다.

런타임 경로 통일: 서버·감시·적용 기록은 `runtime/platform/`입니다. `runtime_layout.py`는 중지된 기존 런타임의 메뉴별 이동·제어 JSON 경로 갱신을 담당합니다. 전체 소속 표는 backend/README.md를 참조하세요.

런타임 이관은 대상 충돌을 먼저 확인하고 경로 이동 후 실제 제어 JSON만 갱신합니다. 복사된 모델 소스·추출된 original 트리는 검색하지 않습니다. 경로 참조 갱신은 한도 내 제어 파일에 한정하며 원본 모델·토크나이저를 검사하지 않습니다.

모듈의 실행 중 작업은 등록된 busy_reason 훅을 통해 공통 재시작 차단 목록에 포함합니다. 모듈 폴더·등록 정보 변경 시 import 사전 확인, 프론트 빌드, 서버 적용을 자동 처리합니다. 작업 중이거나 차단 상태를 확인할 수 없으면 적용을 보류합니다. 프론트 독립 적용은 기존 작업을 중지하지 않습니다.
