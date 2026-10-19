# 앱 설치·실행·제거 백엔드

용도: 프로젝트 관리 소메뉴의 설치 트랜잭션과 앱 소유 파일·연결 수명주기를 담당합니다.

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
- standalone_runner.py: 원래 프로젝트 경로를 찾지 않고 추출한 폴더를 ROOT로 사용합니다. 상속된 PLATFORM_ROOT/PLATFORM_MODULES_DIR/PYTHONPATH/HERMES_HOME을 정리하며 setup/check/run을 제공합니다. 설치는 기존 install_windows.py·module_sources.py를 복사해 재사용합니다. Hermes 모델 실행기는 공개 URL·해시를 내보내 setup에서 검증·설치합니다. Windows 전용 설치이며 모델/키/기존 데이터는 별도 준비합니다.
- development/tests/test_builtin_packages.py: 다른 모듈/비밀/환경 제외, 경로·무결성·실행 환경, 실행기 SHA-256과 압축 경계 검사. 실제 단독 실행 검사는 development/scripts/verify_standalone_modules.py이며 자세한 조건은 상위 README를 따릅니다.

현재 분리 경로: projects/detach는 detachment.start의 비동기 작업으로 실행합니다. 현재 패키지·독립 실행 진입점·필요한 UI를 준비한 뒤 원래 프로그램과 해당 모듈 data 항목을 이동합니다. builtin_record는 기본 모듈을 같은 작업 목록에 등록하고 reconnect_builtin은 원래 위치로 되돌립니다. 롤백 실패 시 파일을 보존하고 오류를 표시합니다.

cleanup.py는 이전 ZIP/가져오기 잔재를 휴지통으로 이동합니다. projects/cleanup·projects/folder/open은 각각 정리와 실제 앱 폴더 열기입니다. requirements.py는 문서 저장소를 실행 앱과 구분합니다. 검증 파일은 development/tests/test_project_detachment.py 및 development/scripts/verify_project_detachment.cjs입니다. Node MCP 연결은 이전 .venv/hermes 대신 modules/hermes/.venv를 사용합니다.

Windows 설치기: powershell_app.py·powershell_metadata.ps1은 원본 PS AST만 읽어 옵션을 탐지합니다. adapters.py의 powershell 유형은 runtime.verify에서 문법만 확인하며 entry_executed로 표시하지 않습니다. 원본 실행은 projects/setup 사용자 요청에서만 별도 프로세스로 시작하며 runtime.ACTIVE로 서버 적용·제거를 보호합니다. setup/folder는 사용자 클릭 시에만 Windows 폴더 선택 창을 엽니다. setup/status는 JSON과 최근 로그만 읽고 매번 PowerShell을 띄우지 않습니다. 임시 다운로드는 해당 설치 버전의 setup-cache에 격리합니다. 원본 설치기가 지정 대상 폴더에 만든 파일은 저장소 제거로 자동 복원/제거되는 대상이 아닙니다. 회귀 명령: .venv/Scripts/python.exe -X utf8 -B -m unittest development.tests.test_project_windows_installer -q.

store.project_folder/install_folder가 프로젝트 관리 앱별 부모/application 경로를 계산합니다. 기존 등록 ID와 실제 저장 폴더 이름을 분리합니다. assign_folder는 유휴 상태에서 기존 폴더를 저장소 이름으로 이동하고 레코드/모듈의 소유 경로를 함께 갱신합니다. 새 소스는 versions/version-N/source에 준비하며 분리/재연결/내보내기/제거는 같은 project_folder 경계를 사용합니다. powershell_app.describe는 설치 대상 매개변수만 managed로 표시하고 start가 앱 내부 경로를 강제 사용해 외부 입력 경로로 설치되지 않게 합니다. 필수 기존 프로그램 입력은 자동 설치 경로로 오분류하지 않습니다.

cli_schema.py: 원본 Python argparse의 정적 실행 명세를 읽고 입력 검증/실행 인수로 변환합니다. 모듈/스크립트를 분석 시 실행하지 않습니다. projects/interface·action은 handlers에서 등록하며 실제 실행은 runtime.run_cli → python_packages.cli_command를 사용합니다. 일반 main.py와 README 참조 도구를 탐지하고 pyproject 함수 진입점을 보존합니다. 동일 앱의 중복 실행을 거절하고 실행 로그를 요청마다 초기화해 이전 도움말/결과가 섞이지 않게 합니다. 검사: development/tests/test_project_automatic_ui.py, development/scripts/verify_automatic_ui.cjs.

현재 업데이트 경로: server.py의 FastAPI와 HTML 첫 화면을 정적으로 발견하면 ui.kind=asgi로 연결합니다. runtime은 원본 ASGI 응답을 제공하고 원래 인증을 유지합니다. 앱 업데이트 때 기존 일반 연결 모듈은 재사용하여 호스트 빌드/재시작을 유발하지 않으며 실제 Git source_commit을 기록합니다. frontend/ProjectApp은 설치 revision 변경 시 iframe을 새로 열고 변경 가능한 화면/자산은 no-store로 제공합니다. data/.gitkeep 같은 추적 파일 유무로 폴더 전체를 제외하지 않고, data 안의 파일별로 Git 추적 여부를 비교해 사용자 DB/인증/설정을 새 버전으로 보존합니다. Git이 관리하는 data 소스는 임의 복사하지 않습니다. 임의 외부 저장소의 모든 데이터 위치까지 자동 추적하는 기능은 아닙니다.

## 원본 앱 대화의 Hermes 하네스 연결

용도: 원본 FastAPI 앱의 async ai_provider.compose(system,user,...) 호출을 설치된 Hermes AIAgent로 전달합니다. 앱 소스를 고치거나 Hermes를 복제하지 않습니다. 지원 규격을 발견한 앱의 설치 정보 → 대화 실행 엔진에서 켜고 끄며 registry의 harness 설정은 앱 업데이트에도 유지합니다. project-zero의 대화/업무 계획/역할 응답이 이 공통 함수를 쓰므로 원래 UI와 사업 승인·DB 기록을 유지합니다.

harness.py는 현재 Hermes의 모델·도구·읽기 권한을 사용하고 앱별 실행 세션을 기록합니다. harness_hook.py/app_worker.py는 비동기 왕복 통신으로 원본 provider 호출 결과를 반환하며 원본의 비동기 전송/상태 조회를 막지 않습니다. ProjectHarness.tsx는 같은 앱 상단에서 작업 내역·승인/질문·해당 앱 작업 중지를 제공합니다. 다른 사용자의 Hermes 작업을 중지하지 않으며 동시 앱 요청은 직렬화합니다. 장기 요청은 원본 앱의 비동기 제출 API를 사용해야 합니다. 일반 HTTP 요청의 기존 60초 제한은 유지합니다.

API: projects/settings(use_harness), projects/harness(GET/POST). 아직 이 함수 규격이 없는 임의 앱까지 자동 변환하지 않습니다. 끄거나 독립 분리/내보내기로 실행하면 원본 provider가 작동하며 독립 앱에 Hermes가 자동 포함되는 기능은 아닙니다. 회귀: development.tests.test_project_harness, 실제 모델 검증 결과는 아래 검증 기록과 구분합니다.

2026-10-19 이전 직접실행 구성 기록(현재 계획/직원 분리 전): 회귀 58개·TypeScript·Vite 적용 통과. 실제 project-zero 기존 UI에서 원래 인증 절차로 로그인하고 하네스 대화를 제출했습니다. Hermes 세션 36c95333a036448f9be507939f0efb4b에서 실제 도구 검색/파일 읽기와 최종 응답을 확인했고 원래 앱 DB와 대화창에 답이 표시됐습니다. 모델에게 내용이 제공되지 않은 임의 검사 문자열을 읽었으며 모델이 삽입한 공백은 제거한 뒤 문자 정보를 비교했습니다. 바이트 단위 복사 일치 검사는 아닙니다. 최종 요청은 약 46.7초·모델 API 3회·도구 이벤트 5개였으며 새 업무 배정은 요청하지 않았습니다. 초기 실제 검사에서 JSON 외 설명과 반복 세션 제목 충돌이 발견돼 응답 형식 보정/별도 앱 세션 생성을 수정했습니다. 승인·질문·중지의 소유권은 회귀 검사로 확인했고 실제 위험 명령/사업 승인/주문/배포/7개 역할 전체를 실행한 검사는 아닙니다.

실행기 development/scripts/verify_project_harness.cjs는 현재 verify_project_zero_live.cjs(실제 인사) → verify_project_zero_task.cjs(대표 배정·직원 파일 읽기)를 순서대로 실행합니다. 원본 화면·로컬 인증·원래 작업 DB·실제 모델을 사용합니다. 과거 임의 확인 파일을 만드는 검사는 대화 맥락을 오염시켜 제거했습니다. 새 두 검사 각각의 --resume은 직전 완료 결과의 화면/기록 확인만 재개하며 새 모델 요청을 보내지 않습니다.

## Project Zero 업무·대화 호환

용도: 원본 대표 대화 → 사업안 → 역할 검토 → 소유자 승인 → 실행·기록 흐름을 유지하면서 플랫폼 연결의 오작동을 보정합니다. `harness_prompt.py`는 현재 지시와 과거 대화를 구분하고, 앱 역할/JSON 응답 규격은 Hermes의 실행별 시스템 지침으로 전달합니다. 과거 검사 요청을 새 인사에 재실행하지 않도록 합니다.

단순 인사에는 과거 실행 기록을 보내지 않습니다. Project Zero의 JSON 계획 계약은 원본 OpenAI 호환 전송의 `response_format=json_object`를 사용하며, 다른 앱의 기존 JSON 반환 검증도 유지합니다. 일반 문장을 임의로 업무 계획으로 바꾸거나 성공 응답을 만들어내지 않습니다. Thinking·도구 설정은 보존합니다.

Project Zero의 JSON 계획/검토 단계는 `application_plan_only`로 외부 도구 없이 구조화 응답을 받습니다. 현재 Ollama는 JSON 문법과 도구 호출 문법을 함께 요청하면 sampler 초기화가 실패합니다. 실제 실행은 원본이 생성한 `agent_task`의 별도 일반 텍스트 하네스 호출에서 설정된 도구를 사용합니다. 전체 앱이나 일반 Hermes 대화의 도구를 비활성화하는 설정이 아닙니다.

직원 `agent_task`의 기존 도구 미지원 문구도 실행 시 `project_zero.provider_system`으로 보정합니다. 연결된 도구로 실제 확인할 수 있는 기능을 제공하며, 공개·지출·메일에 대한 소유자 승인 요구는 유지합니다.

`harness_hook`는 원본 compose의 `max_tokens` 인수도 전달합니다. Project Zero는 원래 provider의 temperature 0.3과 요청별 출력 한도를 실행별 `application_generation`에 반영합니다. 저장된 Hermes 설정이나 다른 앱의 생성 정책을 바꾸지 않습니다. 이전 연결에서는 이 인수들이 누락되어 원본과 다른 생성 조건을 사용했습니다.

원본 엔진의 스트리밍 재시도에서 미완성 앞부분 뒤에 완성 JSON이 이어진 응답도 실제 발견했습니다. 반환 보정은 실제로 디코딩되는 완성 객체만 선택하고, CEO 계획에서는 reply가 없는 내부 업무 객체를 답으로 오인하지 않습니다. 괄호를 덧붙이거나 일반 문장을 가짜 계획으로 변환하지 않습니다.

`project_zero.py`는 이 저장소의 하네스가 켜진 자식 실행기에만 적용됩니다. 원본 소스·UI·DB를 복사하거나 수정하지 않고 부정문 사업 생성, 단순 후속 대화의 초안 수정 오판, 현재 사업/회의 맥락 누락, 도구가 없다는 고정 안내를 보정합니다. 원본 승인 절차를 우회하거나 미구현 제품을 완성했다고 표시하지 않습니다. 원본 대화 함수 구조가 달라지면 호환 오류를 표시합니다.

`runtime.invoke`와 `app_worker`는 실제 플랫폼 HTTP 요청의 Host·접속자를 원본 ASGI에 전달합니다. 호출 본문의 가짜 접속자 정보는 덮어씁니다. 원본의 로컬 자동 로그인은 루프백 접속에만 적용되고 외부 인증 요구는 유지됩니다.

검사: `.venv/Scripts/python.exe -X utf8 -B development/scripts/verify_project_zero.py`. Git 추적 소스 사본·임시 DB에서 원본 업무 검사와 호환 회귀 41개를 통과했습니다. 모델 호출은 모의 응답이며 사용자 모델/기존 DB를 사용하지 않습니다. 임시는 실패 시에도 정리하고 결과를 `runtime/projects/manage/verification/project-zero-workflow.json`에 기록합니다. 실제 모델 대화 확인은 별도 검증이며, 임의 제품 제작·결제·광고·배포 성공을 뜻하지 않습니다.

회의 화면 개선 전 확인(2026-10-19): 원본 업무·호환 36개(임시 DB/모의 모델), 플랫폼 관련 회귀 57개 통과. 실제 원본 UI의 인사는 모델 API 1회·24.1초·도구 0회·업무 0개로 표시됐습니다. CTO README 업무 1개는 원래 큐에서 completed/llm으로 저장됐고 실제 read_file 호출과 화면 표시를 확인했습니다(직원 단계 89.9초·모델 API 6회·도구 4회). JavaScript 오류 0건, 설치된 원본 추적 소스 변경 없음. 결과는 runtime/projects/manage/verification/project-zero-live.json·project-zero-task.json, 화면은 project-zero-live.png·project-zero-cto.png입니다. 중복 상대 경로 재탐색과 9B 요약의 어색하거나 부정확한 표현은 남아 있으며 실제 카드 결제·광고·임의 신제품 배포를 검증한 결과가 아닙니다.

연결된 모델의 계획 생성/파싱 실패는 모델 미연결로 안내하거나 규칙 기반 업무를 대신 생성하지 않습니다. 원본 오류 기록과 오류 설명은 보존하고 이번 요청의 새 업무를 0개로 반환합니다. 모델이 실제 미연결인 원래 규칙 모드는 유지합니다. 오류 주입 회귀는 모의 모델로 확인했습니다.

실제 모델 검사 명령: `node development/scripts/verify_project_harness.cjs --allow-local-model`. 이 검사는 원본 앱의 실제 대화/작업 기록을 남깁니다. 일반 회귀에서는 실행하지 않습니다. 새 두 실행기의 `--resume`은 이미 완료된 자기 검사 기록 확인에만 사용합니다. 최근 인사와 직원 업무를 각각 확인한 직후에 사용해야 하며 임의 다른 작업 결과를 대신 검사하지 않습니다.

## 회의 진행·경영실 보기

용도: `project_zero_state.py`가 기존 앱에 인증된 `/api/admin/platform/workspace` 조회를 추가합니다. 대화/회의/업무/사업안은 원본 DB와 API를 그대로 사용하며 `harness_prompt.stage_for`의 실제 역할/호출 종류를 별도 진행 정보로 제공합니다. 회의 발언 5개와 CEO 종합은 순차 모델 호출이며 업무 큐의 실행 상태가 아닙니다. 앱 재시작 시 복구할 수 없는 running 회의는 발언을 보존한 failed로 표시해 영구 진행 상태를 막습니다.

`project_zero_business.py`는 새 사업 모델 요청의 previous_draft를 빈 값으로 시작합니다. 기존 BASE의 DealPage 예제를 항상 보내던 편향을 제거하고 필수 내용 없는 응답은 실패로 처리합니다. 실제 승인된 DealPage 제품과 기존 사용자 사업안을 삭제하거나 출시 조건을 바꾸지 않습니다. 수익 목표를 의논하는 '월천만원 벌거리'도 새 사업 검토로 연결합니다.

회의/종합은 원본처럼 도구 실행 없는 의견 작성 단계입니다. agent_task 업무만 설정된 실행 도구를 사용합니다. 원본 파일은 변경하지 않으며 원본 UI도 별도로 엽니다. 플랫폼 보기 구현과 확인 방법은 [프론트 안내](../frontend/project_zero/README.md)를 따릅니다.

회의 맥락: project_zero_business.request_options는 기본적으로 회의·사업 검토를 focused_discussion으로 지정합니다. 회사 역할·현재 주제·사용자 시스템 지침은 유지하고, 관련 없는 엔진 개발 지침/공유 기억/검토 쓰기를 해당 요청에만 제외합니다. 직원 agent_task는 원래 도구·맥락을 유지합니다. 전문가 단계는 이전 발언/주제 연결이 없는 과거 교훈을 제외해 먼저 독립 검토하고, CEO는 현재 회의의 전체 발언을 종합합니다. 원본 DB 기록은 삭제하지 않습니다.

/api/admin/platform/discussion-context의 include_engine_context 스위치를 켜면 원본처럼 이전 발언·교훈·엔진 공유 맥락을 다시 포함합니다. 앱 DB settings의 platform_meeting_engine_context에만 보관하고 진행 중 회의에서는 변경을 거절합니다. UI에서 다음 회의·사업 검토 옵션임을 표시하며 전역 Hermes 설정은 변경하지 않습니다.

확인 명령: node development/scripts/verify_project_zero_workspace.cjs는 실제 인증/기록과 별도의 화면 전용 진행 모의 데이터를 사용하며 모델을 실행하지 않습니다. node development/scripts/verify_project_zero_meeting.cjs --allow-local-model은 실제 전문가 5명·CEO 호출 6개와 서로 다른 세션·저장 발언·완료 화면을 확인합니다. 원본 UI 호환 검사는 이제 /assets/projects/<id>/index.html에서 실행합니다.

2026-10-19 회의·경영실 개선 확인: 격리 업무/호환 41개·플랫폼 회귀 60개, TypeScript·Vite 통과. 실제 인증/기록과 화면 전용 진행 모의 데이터로 PC 1440px·모바일 390px의 탭·입력 보존·진행 6단계·가로 넘침 없음·JavaScript 오류 0건을 확인했습니다. 첫 실제 회의는 개발 맥락/앞선 발언의 예제 편향이 발견됐고, 기본 주제 전용 맥락 적용 후 다시 실행한 실제 회의는 전문가 5명·CEO의 6개 독립 세션으로 완료됐습니다. 통제한 시험 주제의 선택되지 않은 예제 상품 언급은 0건입니다. 진행/결과는 project-zero-real-meeting.json, 화면은 project-zero-real-meeting.png·project-zero-workspace-desktop.png·project-zero-workspace-mobile.png입니다. 이는 실제 시장조사·매출·출시 검증이 아니며 모든 모델 응답의 사실성을 보장하는 검사는 아닙니다.

2026-10-19 문맥 격리 보정: skip_context_files/skip_memory만으로는 원본 시스템 프롬프트의 호스트·현재 경로·코딩 맥락·플러그인 구간이 없어지지 않았습니다. focused_discussion은 실행별 프롬프트 빌더를 앱 역할+사용자 지정 지침으로 교체하고 압축 재생성에도 같은 경계를 유지합니다. 일반 native/직원 도구 실행은 변경하지 않습니다. 기존 회의/앱 대화에 저장된 잘못된 추정은 삭제하지 않으며, 과거 기록과 사용자 지정 공유 맥락의 영향은 별개입니다. 회귀는 test_project_harness의 원본 빌더 미호출·캐시 재생성·native 보존 검사로 확인합니다. 수정 후 실제 모델 답변의 주제 혼동 재발 여부는 별도 확인 대상입니다.

회의 실행안: project_zero_meeting.py는 기존 CEO 종합 1회에서 4줄 요약과 담당·단계·산출물·완료 기준이 있는 실행안을 생성합니다(모델 6회 구조 유지). project_zero_plans.py는 앱 DB에 승인 대기로 저장하며 대화창 ExecutionPlanCard의 승인하고 실행/보류에 연결합니다. 승인 전 업무 0개, 승인 시 원본 agent_task 큐에 기획→설계→제작→QA를 순차 등록하고 선행 실제 결과를 넘깁니다. 선행 실패 시 후속 실행 중단, 중복 승인 거절, 인증 필수입니다. 지출·외부 공개·메일은 별도 승인 대상입니다. 잘못된 계획은 회의 실패로 표시하며 임의 고정 실행안으로 대체하지 않습니다. 이전 회의는 바로 실행 승인하지 않고 이 회의로 실행안 작성을 누르면 저장된 발언으로 CEO 종합만 1회 다시 요청합니다. 비동기 작성 상태를 표시하고 중복 작성을 거절하며 기존 기록은 보존합니다. 발언은 상세 기록으로 접고 대표 대화에는 CEO 요약과 승인안만 표시합니다. 실제 모델의 새 실행안 생성·홈페이지 제작·배포 품질은 격리 회귀 검사와 구분해 미확인으로 남깁니다.

실행안 보정 확인: 격리된 원본·업무 검사 46개, 하네스 단위 16개, TypeScript·Vite 통과. 실제 인증과 모의 승인 요청으로 PC1440/모바일390의 요약·접힌 상세·승인 버튼을 확인했으며 DB 업무 생성 없이 중복 클릭·가로 넘침·JS 오류를 검사했습니다. verify_project_zero_context.py는 사용자 모델 대신 로컬 가짜 API에 원본 AIAgent 요청을 보내 호스트/현재 경로가 전송되지 않는 것을 확인합니다(가짜 API 2회). 승인 후 실제 홈페이지 제작·QA 품질·배포는 미확인입니다. 실제 CEO 실행안 생성 결과는 runtime/projects/manage/verification/project-zero-plan-live.json이 있을 때 별도 확인하며, 과거 회의 6회 호출 검사와 구분합니다.

실제 CEO 실행안 검사에서 사업 검증계획 QA를 제작 후 검사로만 취급하는 규칙 오류를 발견했습니다. QA는 앞선 사업·기획·설계 산출물도 검토할 수 있으며, 제작이 포함된 실행안에서는 제작→QA 순서를 계속 강제합니다. 원본 CEO 응답은 앱 settings의 platform_meeting_draft:<회의 ID>에 보존하고 재요청 때 현재 규칙으로 검증해 사용합니다. 복구 불가능한 초안만 모델에 재요청합니다. 승인 카드의 기본 요약은 4줄이며 전체 보고·작업 기준은 상세에 보존합니다.

최종 확인: 격리 업무 검사 47개 통과. 기존 실제 회의의 CEO 종합 1회는 243.6초 후 완료됐고, 초기 규칙 오류로 실패한 원본 응답을 보존·재검증하여 모델 재호출 없이 승인 대기 실행안 4개와 CEO 대화 메시지로 연결했습니다. 실제 승인 버튼 표시, 승인 전 업무 0개, 앱 공유 맥락 false를 확인했습니다(project-zero-plan-live.json/png). 실제 승인 버튼은 누르지 않았습니다. PC1440/모바일390 UI 회귀도 다시 통과했습니다. 모델의 모든 사실 주장이나 홈페이지 제작 성공을 확인한 결과는 아닙니다.
