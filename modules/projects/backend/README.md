# 앱 설치·실행·제거 백엔드

용도: 프로젝트 관리 소메뉴의 설치 트랜잭션과 앱 소유 파일·연결 수명주기를 담당합니다.

FreeLLMAPI는 기존 원본 화면에 [남은 무료 총량 화면 패치](../patches/freellmapi/README.md)를 적용합니다. 공통 Card·Tailwind로 업체 보고 잔여량, 저장된 연결 수, 자동 라우팅 후보, 최근 요청 결과를 표시합니다. 카탈로그 한도나 로컬 사용량으로 잔액을 추정하지 않습니다.

Node HTTP 앱의 `index.html` 진입은 `runtime.py`가 같은 앱의 루트 URL로 307 이동하며 쿼리를 보존합니다. React Router가 문서 파일명을 업무 경로로 해석해 404를 표시하지 않게 합니다. 2026-10-24 기존 FreeLLMAPI 플랫폼 iframe에서 `/models/chat` 원본 화면 표시를 확인했습니다. Codex는 OpenCodex의 단일 `FreeLLMAPI · 자동` 항목을 사용하며, 로컬 활성 체인은 실제 응답을 확인한 네 모델 그룹(여섯 공급 경로)으로 제한했습니다. 카탈로그 전체의 작동을 검증한 것은 아닙니다. 원본 요청/토큰 기록은 확인했지만 업체 대시보드의 잔여 무료 한도 차이는 확인하지 않았습니다.

Node HTTP + Vite 앱은 `package.json`의 실제 `start`/`server` 진입점을 함께 탐지합니다. `node_http_worker.cjs`는 원본 서버의 HTTP 요청을 전용 named pipe(Windows)/Unix socket IPC로 실행하고 `runtime.py`의 기존 `projects/invoke`·단일 `/api`에 연결합니다. 추가 TCP 포트나 앱별 API 서버는 만들지 않습니다. 원본 인증·로컬 접근 판정에 실제 플랫폼 접속자의 주소를 전달하고, 쿠키 세션은 별도 인증 어댑터가 필요하다고 거부합니다. 화면은 기존 `assets_bridge.js`로 API를 연결합니다. Node IPC의 모든 응답·스트림 이벤트에는 요청 ID를 붙이고 `runtime.py`가 요청별 큐로 받습니다. 취소된 스트림의 남은 응답이 다음 인증·대화 요청에 섞이지 않도록 큐를 해제합니다. `verify_ui.cjs`는 같은 원본 Node 서버와 빌드 화면을 실행합니다. 재시도는 저장된 소스·node_modules·빌드 결과를 재사용하며 새 설치·업데이트는 의존성과 화면을 새로 준비합니다. 독립 ZIP 실행은 원본 Node 진입점을 실행합니다.

FreeLLMAPI는 기존 API 호스트의 `/api/projects/freellmapi/<설치 ID>/v1/{models,responses,chat/completions}` 경로를 직접 사용합니다. `handlers.py`는 공식 FreeLLMAPI 설치 원본인지 확인하고 loopback 클라이언트·통합 Bearer 키만 허용한 뒤 `runtime.invoke`로 같은 Node worker에 전달합니다. 허용 경로는 모델 목록·Responses·Chat Completions 세 가지이며, `api_transport.py`도 이 경로만 통과시킵니다. 별도 포트·서버·원본 복사본은 없습니다. IPC worker는 SSE 청크를 즉시 전달합니다. 스트리밍은 10분 무응답 제한, 일반 응답은 15분 제한·64 MiB 상한입니다. Codex 입력과 Node worker의 입력 상한은 원본 LLM API 기본값과 같은 25 MiB입니다. 과거 2 MiB/8 MiB 상한은 긴 대화·이미지를 원본 이전에 차단했고, OpenCodex가 이를 context_length_exceeded로 표시할 수 있었습니다. 9 MiB 입력이 원본 JSON 파서에 도달함을 확인했으며 이 확인에는 모델 추론을 사용하지 않았습니다.

2026-10-24 실제 확인: FreeLLMAPI Chat Completions에서 `gemini-2.5-flash`가 응답했습니다. 같은 API 호스트의 Responses `auto`에서 일반 응답과 Codex식 `encrypted` 필드를 포함한 도구 함수 호출이 완료됐습니다. OpenClaw와 Hermes 공식 CLI도 각각 `auto`에서 `OK`를 반환했습니다. OpenClaw 사용량 기록은 비용 `$0.00`였습니다. 플랫폼 기본 URL `/`은 HTTP 200입니다.

Node 앱 설정의 `PLATFORM_NODE_EXECUTABLE`은 실제 실행과 UI 검증에 사용할 기존 Node 실행 파일을 지정합니다. 비동기 초기화가 있는 원본 서버는 실제 listening 이벤트까지 기다립니다. 이미 `/assets/projects/<설치 ID>/`를 기준으로 빌드한 화면에는 같은 경로를 중복 추가하지 않습니다. `PLATFORM_VERIFY_BROWSER_EXECUTABLE`로 기존 Chromium 계열 브라우저를 검사에 재사용할 수 있으며, 브라우저 시작 실패 때도 원본 실행기를 정리합니다. 이 설정은 공용 로그인 브라우저를 바꾸거나 Chrome을 설치하지 않습니다.

실제 확인(2026-10-21): 기존 Orbit 설치 실패는 Vite 화면만 탐지되어 `/api/history`가 통로 밖으로 요청된 것이 원인이었습니다. 저장된 소스·의존성·빌드를 재사용한 설치 재개로 `ready`, 원본 서버 실행·UI 검사 성공을 확인했습니다. 실제 플랫폼 iframe에서 원본 화면 표시·`/api/history` HTTP 200·JavaScript 오류 0건을 확인했습니다. 모델 추론·전화·WhatsApp·독립 ZIP 실행은 이 변경에서 확인하지 않았습니다.

- `handlers.py` → `manager.py` → 전체 메뉴 매니저 → 단일 `/api`에 등록합니다.
- `installer.py`, `adapters.py`, `node_mcp.py`: 원본 진입점 탐지, 의존성 설치, 실행·UI 확인, 메뉴와 MCP 자동 연결. 모델 변환은 `allow_agent=true`로 명시한 설치·재시도에서만 실행합니다.
- `python_packages.py`: 공용 Python 실행기를 재사용하되 앱 의존성은 해당 소스의 `.platform-runtime/python`에 설치합니다. `app_worker.py`, `runtime.py`는 그 경로를 자식 실행기에만 전달합니다. native 모듈은 공용 의존성이 이미 충족돼야 하며 설치기가 공용 Python을 변경하지 않습니다.
- `lifecycle.py`: 앱 소유 모듈·소스·의존성·설정·기록·내보낸 파일과 MCP 연결을 함께 제거합니다. 분리는 파일을 보관하며 재연결 때 재설치하지 않습니다. 이전 버전에서 공용 Python에 설치한 패키지는 소유 기록이 없으므로 임의로 지우지 않습니다.
- `packages.py`, `package_import.py`: ZIP 내보내기/가져오기. 파일 해시·중복·경로·크기 검증 후 기존 설치 트랜잭션을 재사용합니다. 해시는 손상 검사용이며 게시자 서명은 아닙니다. 다운로드는 `runtime.register_host`의 동일 호스트 파일 경로입니다.
- `portable_runner.py`, `portable_web.py`: ZIP에 포함되는 표준 라이브러리 기반 독립 실행기. 플랫폼·Codex·사용자 모델이 없어도 정적/Vite/FastAPI/Python CLI/Node MCP 원본 실행을 준비합니다. 독립 실행한 앱은 플랫폼과 별개이므로 자체 로컬 웹 포트를 사용할 수 있습니다.
- `localization.py`: 준비된 유휴 모델만 번역에 사용합니다. 번역 때문에 모델을 불러오지 않습니다. 꺼진 모델·작업 중에는 원문을 표시합니다.

API: `projects/install`, `retry`, `settings`, `detach`, `reconnect`, `remove`, `export`, `import`, `agent/connect`, `agent/start`. 데이터와 검사 자료는 `runtime/projects/manage/` 소속입니다. 내보내기는 앱별 `projects/<앱 이름>/exports/`, 가져오기 임시는 `imports/`이며 설치 성공·실패·취소 뒤 정리합니다.

검사 명령·현재 한계·실제 결과는 [상위 안내](../README.md)를 따릅니다. 외부 native 모듈과 임의 데스크톱 앱 변환은 기존 외부 앱 ZIP 대상이 아닙니다. 기본 금융·REA·Hermes는 별도 standalone-module 소스 배포 형식으로 지원합니다.

- builtin_packages.py: finance/rea/hermes만 받아 선택 모듈·공통 호스트/UI 소스 복사본·의존성 명세·전용 설치/실행 진입점을 ZIP에 넣습니다. 다른 모듈·실제 가상환경·데이터·비밀 설정은 제외합니다. 기존 projects/export와 안전한 project-packages 다운로드 경로를 사용합니다.
- standalone_runner.py: 원래 프로젝트 경로를 찾지 않고 추출한 폴더를 ROOT로 사용합니다. 상속된 PLATFORM_ROOT/PLATFORM_MODULES_DIR/PYTHONPATH/HERMES_HOME을 정리하며 setup/check/run을 제공합니다. 설치는 기존 install_windows.py·module_sources.py를 복사해 재사용합니다. Hermes 모델 실행기는 공개 URL·해시를 내보내 setup에서 검증·설치합니다. Windows/macOS 설치 분기를 사용하며 모델/키/기존 데이터는 별도 준비합니다. Mac의 금융 CUDA·키움 설치는 지원하지 않습니다.
- development/tests/test_builtin_packages.py: 다른 모듈/비밀/환경 제외, 경로·무결성·실행 환경, 실행기 SHA-256과 압축 경계 검사. 실제 단독 실행 검사는 development/scripts/verify_standalone_modules.py이며 자세한 조건은 상위 README를 따릅니다.

현재 분리 경로: projects/detach는 detachment.start의 비동기 작업으로 실행합니다. 현재 패키지·독립 실행 진입점·필요한 UI를 준비한 뒤 원래 프로그램과 해당 모듈 data 항목을 이동합니다. builtin_record는 기본 모듈을 같은 작업 목록에 등록하고 reconnect_builtin은 원래 위치로 되돌립니다. 롤백 실패 시 파일을 보존하고 오류를 표시합니다.

cleanup.py는 이전 ZIP/가져오기 잔재를 휴지통으로 이동합니다. projects/cleanup·projects/folder/open은 각각 정리와 실제 앱 폴더 열기입니다. requirements.py는 문서 저장소를 실행 앱과 구분합니다. 검증 파일은 development/tests/test_project_detachment.py 및 development/scripts/verify_project_detachment.cjs입니다. Node MCP 연결은 이전 .venv/hermes 대신 modules/hermes/.venv를 사용합니다.

Windows 설치기: powershell_app.py·powershell_metadata.ps1은 원본 PS AST만 읽어 옵션을 탐지합니다. adapters.py의 powershell 유형은 runtime.verify에서 문법만 확인하며 entry_executed로 표시하지 않습니다. 원본 실행은 projects/setup 사용자 요청에서만 별도 프로세스로 시작하며 runtime.ACTIVE로 서버 적용·제거를 보호합니다. setup/folder는 사용자 클릭 시에만 Windows 폴더 선택 창을 엽니다. setup/status는 JSON과 최근 로그만 읽고 매번 PowerShell을 띄우지 않습니다. 임시 다운로드는 해당 설치 버전의 setup-cache에 격리합니다. 원본 설치기가 지정 대상 폴더에 만든 파일은 저장소 제거로 자동 복원/제거되는 대상이 아닙니다. 회귀 명령: .venv/Scripts/python.exe -X utf8 -B -m unittest development.tests.test_project_windows_installer -q.

store.project_folder/install_folder가 프로젝트 관리 앱별 부모/application 경로를 계산합니다. 기존 등록 ID와 실제 저장 폴더 이름을 분리합니다. assign_folder는 유휴 상태에서 기존 폴더를 저장소 이름으로 이동하고 레코드/모듈의 소유 경로를 함께 갱신합니다. 새 소스는 versions/version-N/source에 준비하며 분리/재연결/내보내기/제거는 같은 project_folder 경계를 사용합니다. powershell_app.describe는 설치 대상 매개변수만 managed로 표시하고 start가 앱 내부 경로를 강제 사용해 외부 입력 경로로 설치되지 않게 합니다. 필수 기존 프로그램 입력은 자동 설치 경로로 오분류하지 않습니다.

cli_schema.py: 원본 Python argparse의 정적 실행 명세를 읽고 입력 검증/실행 인수로 변환합니다. 모듈/스크립트를 분석 시 실행하지 않습니다. projects/interface·action은 handlers에서 등록하며 실제 실행은 runtime.run_cli → python_packages.cli_command를 사용합니다. 일반 main.py와 README 참조 도구를 탐지하고 pyproject 함수 진입점을 보존합니다. 동일 앱의 중복 실행을 거절하고 실행 로그를 요청마다 초기화해 이전 도움말/결과가 섞이지 않게 합니다. 검사: development/tests/test_project_automatic_ui.py, development/scripts/verify_automatic_ui.cjs.

현재 업데이트 경로: server.py의 FastAPI와 HTML 첫 화면을 정적으로 발견하면 ui.kind=asgi로 연결합니다. runtime은 원본 ASGI 응답을 제공하고 원래 인증을 유지합니다. 앱 업데이트 때 기존 일반 연결 모듈은 재사용하여 호스트 빌드/재시작을 유발하지 않으며 실제 Git source_commit을 기록합니다. frontend/ProjectApp은 설치 revision 변경 시 iframe을 새로 열고 변경 가능한 화면/자산은 no-store로 제공합니다. data/.gitkeep 같은 추적 파일 유무로 폴더 전체를 제외하지 않고, data 안의 파일별로 Git 추적 여부를 비교해 사용자 DB/인증/설정을 새 버전으로 보존합니다. Git이 관리하는 data 소스는 임의 복사하지 않습니다. 임의 외부 저장소의 모든 데이터 위치까지 자동 추적하는 기능은 아닙니다.

## 원본 앱 대화의 Hermes 하네스 연결

용도: 원본 FastAPI 앱의 async ai_provider.compose(system,user,...) 호출을 설치된 Hermes AIAgent로 전달합니다. 앱 소스를 고치거나 Hermes를 복제하지 않습니다. 지원 규격을 발견한 앱의 설치 정보 → 대화 실행 엔진에서 켜고 끄며 registry의 harness 설정은 앱 업데이트에도 유지합니다.

harness.py는 현재 Hermes의 모델·도구·읽기 권한을 사용하고 사용자 대화 세션을 생성하지 않고 앱 요청을 실행합니다. harness_hook.py/app_worker.py는 비동기 왕복 통신으로 원본 provider 호출 결과를 반환하며 원본의 비동기 전송/상태 조회를 막지 않습니다. ProjectHarness.tsx는 같은 앱 상단에서 작업 내역·승인/질문·해당 앱 작업 중지를 제공합니다. 다른 사용자의 Hermes 작업을 중지하지 않으며 동시 앱 요청은 직렬화합니다. 장기 요청은 원본 앱의 비동기 제출 API를 사용해야 합니다. 일반 HTTP 요청의 기존 60초 제한은 유지합니다.

API: projects/settings(use_harness), projects/harness(GET/POST). 아직 이 함수 규격이 없는 임의 앱까지 자동 변환하지 않습니다. 끄거나 독립 분리/내보내기로 실행하면 원본 provider가 작동하며 독립 앱에 Hermes가 자동 포함되는 기능은 아닙니다. 회귀: development.tests.test_project_harness, 실제 모델 검증 결과는 아래 검증 기록과 구분합니다.

일반 설치 경로는 저장소 이름에 따른 전용 처리를 적용하지 않습니다. 명시적인 company-v1 연결은 현재 Hermes 영구 세션과 원본 회사 UI/기록 어댑터를 사용합니다. 별도 회사 planner/provider/직원 scheduler는 실행하지 않습니다. 현재 구조와 검사는 backend/README.md 및 integrations/README.md를 따릅니다.

정리 확인: Project Zero 내부 세션 35개·메시지 123개를 원본 SessionDB 삭제 기능으로 제거하고 나머지 29개 세션 보존을 확인했습니다. 전용 소스·검사 자료와 대상 대화 백업은 프로젝트 휴지통에 보관하며 Git에 포함하지 않습니다.

정리 후 검증: 공통 프로젝트 관리 회귀 62개·TypeScript 통과. 실제 서버 화면에 모의 재설치 정보를 제공해 원본 iframe 표시·전용 경영실 미적용·JavaScript 오류 0건을 확인했습니다. 실제 GitHub 재설치와 모델 추론은 실행하지 않았습니다.

## Hermes 총괄과 회사 기록 통합

용도: Project Zero 원본 UI와 회사 기록을 유지하면서 대화·기억·판단·실행은 기존 Hermes에 맡깁니다.

- `workspaces.py` / `workspace_embed.js`: 명시적인 company-v1 연결의 고정 원본 HTML(회사 현황·업무 실행 기록)을 유지합니다. 모델 표시와 설정 이동은 실제 Hermes 상태를 사용합니다.
- `conversation.py`: `action=session`은 원본 CEO 과거 기록을 최초 한 번만 native SessionDB로 이관하고, 설치 ID에 대응하는 영구 세션을 재사용합니다. 이후 대화는 원본 CEO DB에 이중 저장하지 않습니다. 원본 DB는 과거 기록과 사업안·승인·업무·회의록을 보존합니다.
- `integrations/company_records.py`: 앱 소유 `integrations/hermes/workflow.py`에 설치되는 기록 어댑터입니다. 기존 파일 해시를 확인한 뒤 원자적으로 갱신하고 저장 실패 시 복원합니다. 원본 planner/provider/직원 scheduler는 실행하지 않습니다. 회사 API 인증은 유지합니다.
- `projects/company-tool`: 세션별 내부 capability로 회사 조회·초안·업무 시작/종료·회의록을 연결합니다. 모델 도구로 사업 승인을 위조할 수 없습니다. 소유자 결정은 별도 `projects/conversation action=decision`으로 받습니다.
- `modules/hermes/backend/chat/company.py`: 원본 도구 registry에 회사 도구를 추가합니다. 일반 파일·터미널·기억·delegation과 원본 chat/Goal/Loop를 그대로 사용합니다. 고정된 CPO→CTO→QA 파이프라인은 없습니다. 대표가 직접 맡긴 작업은 사업안 없이 기록할 수 있습니다.
- `harness.py` / `harness_hook.py`의 provider 실행은 다른 설치 앱 호환용입니다. 회사 탭의 status/control은 같은 native 작업의 상태·측정·승인·소유 중지만 전달하고, 실행 중 제거/적용을 보호합니다. native 총괄 대화는 이 경로, SERIAL, application_request, focused_discussion을 거치지 않습니다.

현재 검증: 관련 백엔드 회귀 37개·TypeScript 통과. 원본 Hermes 경계 검사에서 기존 13개 통과와 새 native 회사 세션 검사의 성공을 각각 확인했습니다. 새 검사는 동일 ID 재사용·원본 과거 문맥·native 회사 도구/파일 도구·재시작 후 SessionDB 보존을 실제 원본 엔진과 모형 HTTP 모델로 확인합니다. 이것은 실제 사업 제작 성공을 뜻하지 않습니다.

실제 선택 모델의 제작 수행·브라우저 확인 결과는 Hermes chat README와 runtime/ai_agent/Hermes/verification/workspace-tabs 자료에 구분합니다. 외부 공개·결제 연동·매출·파인튜닝·강화학습은 별도 확인 대상입니다. 과거 승인 견적서 작업은 요구사항 작성 뒤 CTO 시간 초과/QA 미실행 상태였으며 그 실패 기록을 지우지 않습니다.

workspace/connect는 설치 모듈의 workspace_host를 기록해 별도 실행 메뉴를 Hermes 탭으로 통합합니다. conversation state는 승인된 사업의 실제 dist/index.html 존재를 확인해 preview_url을 제공합니다. 공개/결제 상태를 완료로 바꾸지 않습니다.

회사 기록 도구 recall/remember는 기존 회사 DB의 업무·사업·회의·경험·교훈을 재사용합니다. 새 DB나 별도 학습/검색 서버를 만들지 않습니다. 기존 conversation의 capability 인증 아래 동작하며 native CEO가 같은 조직 SessionDB 기록과 함께 제한된 문맥으로 조회합니다. 사업별 최신 결정의 정정·진행 중 업무·실패 근거는 integrations/README.md를 따릅니다.

회사 대화 상태: conversation.py의 projects/conversation은 기존 승인 사업의 작업 폴더에서 dist/index.html을 확인해 progress.ready_products를 집계합니다. progress.approved는 승인 프로젝트 수이며 실제 실행 프로세스 수를 뜻하지 않습니다. 제품 준비 수는 모든 승인 사업을 확인하고 기존 첫 제품 미리보기 연결은 유지합니다.

회사 이름 투영: company-v1의 기존 JSON 응답은 runtime.py에서 Hermes의 현재 개별 프롬프트 이름으로 투영합니다. 직원 참조는 불변 staff_id로 이관하고 자연어 기록 원문은 보존하며 설정·회의·회사 카드·업무 필터에는 같은 표시 이름을 사용합니다. workspace_embed.js는 기존 카드 자식 구조를 보존하고 이름 요소만 갱신합니다. 새 DB·추가 서버·재설치는 없습니다.

사업 진행 응답은 폐기된 고정 상점 brand 값을 노출하지 않습니다. 승인 사업과 실제 빌드 파일로 결과물 이름·준비 상태를 표시하며, 실제 서비스 여부는 산출물 실행 확인과 구분합니다.

macOS 실행: node-mcp는 같은 Hermes 전용 환경의 bin/python을 사용합니다. 복사된 Windows wheel은 macOS에서 실행할 수 없으므로 해당 앱 .platform-runtime/python 패키지를 Mac용으로 설치해야 합니다. 원본 소스·DB·제품을 재설치하지 않습니다. runtime.py는 종료된 앱 worker를 다음 요청에서 다시 생성해 패키지 복구 뒤에도 이전 오류가 계속 남는 현상을 방지합니다.

## macOS 실행 경계
용도: 기존 프로젝트 관리/설치/분리/내보내기의 native 실행 경로입니다. adapters·node_mcp는 공유 platform_native.npm_command로 npm 심볼릭 링크를 해석합니다. folder/open은 Finder를 사용하며 Windows 설치기는 Mac에서 실행하지 않습니다. 기존 외부 앱 portable_runner는 같은 Windows 경계를 명시합니다.

builtin_packages와 detachment는 기존 run.py와 함께 실행 가능한 .command 진입점을 제공합니다. standalone_runner의 Mac setup은 같은 공통 설치기·Node/npm을 사용하고 Hermes Metal 실행기는 설치된 Homebrew 바이너리에 연결합니다. Mac engine.json에 Windows 공개 배포 해시가 없으면 그 키를 강제 조회하지 않습니다. 금융 CUDA·키움 환경은 Mac setup에서 설치 전에 거절합니다. 기존 Windows .cmd·공개 배포 해시 검사는 유지합니다.

2026-10-22 공통 npm의 실제 버전 실행·수정 소스 구문을 확인했습니다. 기존 프로젝트를 다시 설치/내려받거나 분리·ZIP 생성하지 않았으므로 외부 앱 설치/배포 완주와 Finder GUI 조작은 미확인입니다. 공통 실행 경로 결과는 ../../../backend/README.md를 따릅니다.

회사 도구 인증은 앱 비밀 토큰과 Hermes의 실제 회사 연결을 함께 검증합니다. conversation.py는 고정 대표 세션 외의 새 총괄 대화도 같은 company_id일 때 허용하고, 업무 기록은 실제 세션별로 소유하게 합니다. 일반 대화를 회사 세션으로 취급하거나 임의 session_id를 신뢰하지 않습니다. 관련 실제 확인은 integrations/README.md를 따릅니다.

Codex 자동 모델의 컨텍스트 등록은 실제 활성 풀의 최소 크기인 131,072 토큰으로 조정했습니다. 생성된 OpenCodex 카탈로그의 자동 압축 기준은 117,964 토큰입니다. 이 값은 연결 본문 크기 제한과 별개이며 실행 중 Codex가 보관한 모델 정보의 갱신 여부·이 긴 대화 전체의 재전송 성공은 별도 확인 대상입니다.

Codex 도구 호환: 원본의 [codex-compatibility.patch](../patches/freellmapi/codex-compatibility.patch)는 Gemini가 거부하는 encrypted 스키마 주석을 제거하고 같은 이름의 실제 인수는 보존합니다. 관련 검사 21개, 원본 서버 TypeScript 빌드, 해당 중첩 주석을 포함한 실제 무료 자동 경로의 함수 호출/결과 반환을 확인했습니다. 큰 Codex 부가 헤더는 원본 Node 서버에 그대로 전달하지 않으며, 같은 EPIPE 재현 요청은 수정 후 HTTP 200을 확인했습니다. 실제 Codex 화면의 전체 기능 확인과 구분합니다.

2026-10-25 공용 연결 복구: 요청별 IPC 큐를 적용해 이전 응답이 다음 모델·인증 요청에 섞이던 문제를 수정했습니다. 실제 자동 세션 발급·인증 완료·대시보드 표시와 Hermes/OpenClaw의 `auto` 대화를 확인했습니다. 설정 소유·프로필별 적용은 각 원본 모듈의 backend/README.md, 화면/한도 설명은 [FreeLLMAPI 패치 안내](../patches/freellmapi/README.md)를 따릅니다.
