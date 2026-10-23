# Backend platform

용도: 공통 호스트의 API 등록·모듈 실행·런타임 소유와 검사 연결을 안내합니다.

| 위치 | 역할 |
| --- | --- |
| [modules/finance/](../modules/finance/README.md) | 금융 대메뉴: 사용자 화면 5개 및 숨김 관리 메뉴 |
| [modules/rea/](../modules/rea/README.md) | 독립 REA 프로젝트: program_analysis/, project_explorer/ |
| [modules/hermes/](../modules/hermes/README.md) | Hermes 프로그램: 엔진·채팅·모델·세션·MCP·스킬. 데이터는 runtime에 보존 |
| [modules/projects/](../modules/projects/README.md) | 공개 GitHub 검색·주소 등록·설치·실행 확인·원본 화면 연결·분리 |
| [AI 에이전트](ai_agent/README.md) | 원본 Hermes·OpenClaw의 실제 중메뉴·소메뉴 매니저·원본 실행 연결 |
| [오버로드](overlord/README.md) | 나자릭 중메뉴·공통 기반·연결 정의·등록 확인·기록 |
| [platform_modules.py](platform_modules.py) | modules/*/module.json 탐색·Python 등록·실행 보호 훅 |
| [menu_registry.py](menu_registry.py) | 모듈 등록 정보를 취합하는 총괄 |
| [web_api.py](web_api.py) | 단일 /api 진입점; 총괄만 통해 기능 등록 |
| [platform_native.py](platform_native.py) | OS별 npm·브라우저 탐색·폴더 열기; 표준 라이브러리만 사용, 설치·모델 호출 없음 |
| api_context.py, api_transport.py | 공유 HTTP 객체·요청 전달·React 제공 |
| runtime/rea/project_explorer/projects/ | 저장된 원본·추론 분석 결과; 실행 기능 등록 대상이 아니며 Git 제외 |

하위 기능 → 소메뉴 매니저 → 대메뉴 → 전체 메뉴 매니저 → API.
각 프로젝트와 작은 메뉴 README를 먼저 읽습니다. 새 프로젝트의 등록 규격은 [modules/README.md](../modules/README.md)입니다. 기능은 자기 매니저로 취합하며 중앙 파일에 프로젝트별 import를 추가하지 않습니다. 구조 이름은 영문 ASCII입니다.

운영 호스트는 `.venv/platform`을 사용합니다. 실제 업무 패키지와 소스는 각 모듈 내부에 있으며, 이전 루트 `.venv`는 개발 검사·복구용입니다. `__pycache__/`는 Python 캐시입니다.

## 런타임 소속

외부 HTTP 진입점은 단일 `/api`입니다. 소메뉴 모듈 → 대메뉴 매니저 → menu_registry 총괄의 import·등록 계층을 유지하며, 런타임은 아래 소유 메뉴에 저장합니다.

| 위치 | 소유 기능 |
| --- | --- |
| runtime/platform/ | 공통 서버·적용·감시 |
| runtime/finance/operation_control/ | 자동 운영·시세 수신·선택 정책 |
| runtime/finance/virtual_account_orders/ | 가상계좌 원장 |
| runtime/finance/policy_learning/ | 정책·학습 작업·Replay·평가 |
| runtime/finance/all_backend_features/results/ | 원본 모듈 수동 실행 결과 |
| runtime/finance/moe/ | Expert 실행 상태·구성 작업 |
| runtime/rea/program_analysis/ | 분석 입력·도구·임시 자료 |
| runtime/rea/project_explorer/projects/ | 저장한 분석 프로젝트 |
| runtime/ai_agent/Hermes/ | 헤르메스 대화·세션·설정·MCP·스킬 |
| runtime/overlord/nazarick/ | 나자릭 연결 정의·실제 확인 기록 |
| runtime/shared/engines/ | 여러 메뉴가 공유하는 실행기 |

별도 생성 파일이 없는 메뉴는 빈 런타임 폴더를 만들지 않습니다. 원본 모델과 모델별 JSON은 사용자 지정 모델 폴더를 사용하며 현재 Mac은 프로젝트 모델/을 사용합니다. 기존 런타임 이동은 development/scripts/runtime_layout.py가 담당하며 서버·감시기·작업 프로세스를 중지한 상태에서만 사용합니다. 같은 이름의 목적지가 있으면 덮어쓰지 않습니다. 원본 모델을 역직렬화하거나 변환하지 않습니다.

호스트 API 컨텍스트는 금융 라이브러리를 import하지 않습니다. module_runtime.py가 모듈별 실행 명령을 선택하고 JSON-line IPC/ASGI 응답만 연결합니다. Python 금융·REA와 Node 어댑터는 같은 규격을 사용합니다. platform_state_io.py는 호스트 자체 상태 입출력입니다. stockrl/·rea/에는 이전 import를 위한 연결만 남았습니다.

## 모듈 분리·재연결 보호 점검 — 2026-10-18

담당: module_runtime.py의 전용 프로세스 요청 접수·재시작 예약·종료입니다. 요청 접수 잠금은 응답 읽기 잠금과 분리하며, busy 확인 시작부터 예약 완료까지 새 요청을 대기시킨 뒤 거절합니다. 예약 취소가 끝나야 접수를 재개합니다. shutdown은 실행기가 이미 종료됐거나 없는 경우 새 프로세스를 시작하지 않습니다. 데이터·소스 경로를 이동/삭제하지 않습니다.

확인: development/tests/test_module_runtime.py에서 두 결함을 수정 전 실패로 재현했습니다. 수정 후에는 실제 Node IPC의 예약·거절·취소·응답·종료, Python 환경 이동 후 명령 실행, 업무 모듈 없는 호스트, 의존성 실패 격리와 큰 파일 전달을 검사합니다. 모듈 등록/탈착·상태 보존은 test_platform_modules.py를 따릅니다. 검사 명령은 `.venv/Scripts/python.exe -X utf8 -B -m unittest discover -s development/tests -p test_module_runtime.py -q`이며 `test_platform_modules.py`도 같은 방식으로 실행합니다. 테스트 임시 소스·로그는 runtime/platform/module-verification 아래 각 임시 폴더에서 생성하고 정리합니다. 완전 독립 배포·다른 PC 실행은 이 검사로 확인하지 않습니다.

등록 상태: health의 module_signature는 호스트 시작 시 로드한 모듈 서명입니다. 감시기는 디스크뿐 아니라 실제 API·프론트/백엔드 적용 기록도 비교해 빠른 제거 후의 메뉴 잔재를 정리합니다. 실제 분리/복원 결과는 projects README를 따릅니다.

## 공통 백엔드 오류 격리

menu_registry.catalog는 한 모듈의 actions 조회 실패를 module_errors에 기록하고 정상 메뉴/명령을 유지합니다. platform_context의 상태 API는 모듈별 views/module_errors를 병합하며 잘못된 응답/예외가 있으면 마지막 정상 상태와 모듈 오류를 함께 반환합니다. 실패를 정상 검증으로 바꾸지는 않습니다.

작업 상태 확인 훅이 실패하면 해당 모듈 이름과 오류를 재시작 차단 사유로 반환합니다. 재시작 예약 중 실패해도 이미 예약한 다른 모듈의 취소를 모두 시도하고 최초 오류를 보존합니다. 종료 실패 시 호스트 재시작 상태를 해제하고 각 모듈 예약 취소를 시도한 뒤 HTTP 409를 반환합니다. 취소 훅 자체의 실패는 로그에 남깁니다.

재현/회귀: development/tests/test_host_resilience.py. 실제 운영 로그에서 메뉴 조회의 RuntimeError가 전체 상태 API까지 전파되던 경로를 확인했고, 나머지 오류·복구 조건은 업무 모듈 대신 검사 훅/임시 폴더로 재현합니다. 검사에서 사용자 모델·시세·학습·매매는 실행하지 않습니다.

2026-10-18 확인: 신규 오류 재현 8개는 수정 전 모두 실패했고 수정 후 관련 호스트/프로세스/등록/감시/프로젝트 수명주기 검사 총 35개가 통과했습니다. 8766에 적용한 뒤 health·등록 모듈 5개 available·상태/카탈로그 오류 없음·실행 차단 작업 없음까지 확인했습니다. 실제 금융 시세·학습·추론·주문 전체 회귀는 이번 점검에서 실행하지 않았습니다. 현재 서버 확인 자료는 runtime/platform/verification/host-resilience.json입니다.

macOS 호스트도 같은 `/api`와 모듈 등록을 사용합니다. api_transport.UnifiedAPI는 전달 시점의 실제 scope를 병합해 FastAPI 수명주기 상태를 유지합니다. 호스트 FastAPI 버전은 development/scripts/requirements/platform.txt에 고정하며, 모듈 전용 패키지 환경과 분리합니다. Mac 실행과 확인 범위는 루트 README를 봅니다.

Mac 모듈 실행: module_runtime.command는 공통 native_runtime_path로 Windows 표기의 경로 구분자와 Python/llama 실행 파일 경로를 해석합니다. platform_modules도 같은 변환으로 리소스 정보를 제공하므로 Mac API에 Windows 실행 경로를 표시하지 않습니다. 원본 module.json은 바꾸지 않아 다른 OS의 설치 정보를 보존합니다. module_sources의 기존 환경 hook이 공유 표준 라이브러리 도구 platform_native를 연결하며, 다른 메뉴의 업무 패키지는 import하지 않습니다. npm_command는 npm 심볼릭 링크의 실제 npm-cli.js를 Node로 직접 실행하고, browser_executable은 macOS 앱/Windows 설치/Linux 실행 경로를 선택합니다. open_folder는 Mac Finder(open), Windows startfile, Linux xdg-open을 사용합니다. 사용자 권한·데이터 저장 경계와 단일 /api는 유지합니다.

2026-10-22 실제 적용: 기존 실행 중이던 REA worker에는 새 .pth hook이 재실행되지 않아 platform_native import 오류와 재시작 보호가 발생했습니다. 자식 작업이 없는 해당 REA 프로세스만 확인·종료한 뒤 같은 적용 경로로 정상 교체했습니다. 이후 health=ok, Hermes=idle/계정 연결 remote·native browser ready, rea/status 정상, 기존 REA 저장 기록 11개 조회를 확인했습니다. 프론트 변경이 없어 재빌드하지 않았고 기존 React 빌드를 유지했습니다. 모델 호출·새 프로젝트/제품·추가 설치는 하지 않았습니다. GUI 선택창/Finder/보이는 브라우저 조작·외부 앱 재설치·분리/ZIP 완주는 미확인입니다.
