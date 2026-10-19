# 프로젝트 설치·관리 안내

용도: GitHub·앱 파일에서 설치한 프로그램의 실행과 분리·재연결·완전 제거를 담당합니다.

**설치**를 누르면 실행 유형 탐지 → 의존성 준비 → 실제 실행 확인 → 화면·메뉴 연결을 자동 처리합니다. 설치 오류가 나도 모델을 임의로 불러오지 않습니다. 미지원 구조의 모델 자동 변환은 사용자가 설치 화면이나 앱 설정에서 켠 경우에만 실행합니다. 한국어 번역은 사용자가 켠 경우에만 이미 준비된 유휴 모델을 사용합니다.

## 구현과 연결

- `backend/adapters.py`, `node_mcp.py`: 정적 HTML·Vite·FastAPI·Python CLI·Node stdio MCP·플랫폼 모듈 탐지. MCP는 원본 manifest의 정확한 npm 버전과 배포 저장소를 확인합니다.
- `backend/installer.py`: 저장된 설치 작업·검증·게시. MCP는 `agent_tasks.link_when_idle`까지 실행한 뒤 활성화합니다. 기존 에이전트 작업 중이면 완료를 기다리며 취소할 수 있습니다.
- `backend/agent_tasks.py`: 저장소별 코드를 추가하지 않는 에이전트 연결·자연어 작업 시작. 원본 Hermes의 `mcp/project`와 `chat`을 호출합니다. 연결된 실제 도구 이름을 요청에 맞춰 안내하며 결과를 지어내지 않도록 지시합니다.
- `backend/runtime.py`, `app_worker.py`, `mcp_worker.py`: 원본 웹 UI·ASGI·MCP 실행. 메뉴별 HTTP 서버를 추가하지 않습니다.
- `backend/lifecycle.py`: 분리·재연결·완전 제거. `backend/handlers.py` → `manager.py` → 플랫폼 총괄의 단일 `/api` 구조입니다.
- `backend/python_packages.py`: 공용 실행기는 재사용하고 Python 의존성은 앱의 `.platform-runtime/python`에 설치합니다. 앱 제거에 함께 포함하며 공용 Python을 변경하지 않습니다. 예전 버전에서 공용 환경에 설치한 패키지는 소유 기록 없이 임의 제거하지 않습니다.
- `backend/packages.py`, `package_import.py`, `portable_runner.py`, `portable_web.py`: 독립 실행 ZIP과 파일 설치. 자세한 소유 경계·직접 연결은 [백엔드 안내](backend/README.md)를 봅니다.
- `frontend/ProjectApp.tsx`: 원본 UI가 있으면 표시하고, MCP에는 `ProjectTask.tsx`의 대상·요청·작업 시작 화면을 자동 선택합니다. 수동 도구/JSON은 개발자 상세에만 있습니다. 다른 종류는 기존 공통 실행/기능 UI를 사용합니다.
- `frontend/ProjectSettings.tsx`: 즉시 열리는 공통 Drawer로 상태·환경 설정·설치 로그를 표시합니다.
- `backend/localization.py`, `project_language.js`, `frontend/useKorean.ts`: 로컬 모델 번역 캐시. 검색 설명과 지원 웹앱의 표시 문자열을 한국어로 변환하고 원본 소스는 바꾸지 않습니다. 번역이 없어도 설치할 수 있습니다. 코드·식별자·제품명은 보존하며 임의의 네이티브 앱·모든 CSP/동적 UI까지 한글화한다고 보장하지 않습니다.

## 사용과 데이터

메뉴: GitHub → 프로젝트 관리 → GitHub에서 추가/설치된 프로젝트. 설치 앱은 GitHub → 앱 이름(중메뉴) → 실행/앱 기능으로 등록합니다. 기존 설치본도 등록 시 같은 규칙을 적용하며 주소·API·런타임은 `projects/`로 유지합니다. Hermes의 MCP 검색·설치는 AI 에이전트 → 헤르메스 → MCP에 속합니다. API: `projects/install`, `retry`, `detach`, `reconnect`, `remove`, `export`, `import`, `detail`, `settings`, `agent/connect`, `agent/start`, `localize`. 검색은 30개씩 더 보기·정렬을 제공합니다.

- **분리:** 다운로드 없이 `projects/<앱 이름>/standalone/`에 실행 진입점·현재 전용 의존성을 자동 준비하고 실제 프로그램 폴더를 옮깁니다. 기본 금융·REA·Hermes는 소유 런타임/DB도 함께 옮기며 다른 모듈 데이터와 공유 실행기는 이동하지 않습니다. 분리 폴더의 실행.cmd로 바로 실행할 수 있습니다. 준비 중 단계와 메뉴 해제 대기를 표시하고 실패하면 원래 위치로 복원합니다.
- **다시 연결:** 실제 프로그램·전용 환경·소유 데이터를 되돌립니다. 다운로드·모델 변환을 다시 실행하지 않습니다. 기본 모듈의 남은 실행 템플릿은 사용자가 수정한 파일도 보존하도록 휴지통으로 옮깁니다. 위치 충돌이나 독립 실행 중인 프로세스가 있으면 덮어쓰지 않습니다. 예전 분리본도 호환합니다.
- **내보내기:** 정적/Vite/FastAPI/Python CLI/Node MCP 앱의 소스·실행 설명·독립 실행기를 ZIP으로 저장합니다. 다른 폴더에서 `python run.py setup`, `check`, `run`으로 원본 기능을 실행하거나 **앱 파일에서 설치**로 가져옵니다. 모델·DB·로그·data/runtime 폴더·비밀 설정은 포함하지 않으며 필요한 외부 서비스/키는 새 환경에 설정해야 합니다. 가져오기는 원본 설치/검증 경로를 재사용합니다. ZIP 32 MiB·소스 128 MiB 한도, 파일 해시·경로·중복 검사, 가져오기 임시 파일 정리를 적용합니다.
- **제거:** 사용자의 완전 삭제 요청에 따라 해당 외부 프로젝트의 모듈·설치 파일·설정·기록을 영구 삭제합니다. 공유 실행기·원본 모델·다른 프로젝트는 삭제하지 않습니다. 일부 파일이 잠기면 제거 실패로 남겨 재시도하게 합니다. 과거 제거에서 휴지통으로 옮겨진 별도 항목이 자동 소멸한 것은 아닙니다.

기본 금융·REA·Hermes도 분리/다시 연결을 제공합니다. 전달용 ZIP은 설치 정보의 개발자 상세에 있습니다. 기존 설치본은 이 외부 설치기의 완전 제거 대상으로 취급하지 않습니다. 특히 기존 REA와 설치한 morluto/rea는 별도 프로젝트입니다.

설치 폴더는 `projects/project-zero/versions/version-1/source/`처럼 저장소 이름과 순번을 사용합니다. 기존 주소/등록 ID는 호환성을 위해 유지하며 같은 저장소 이름이 겹칠 때만 소유자 이름을 붙입니다. 기존 폴더를 이동하면 설정과 모듈의 소유 경로도 함께 갱신하며 충돌은 덮어쓰지 않습니다.

실제 FastAPI 서버의 HTML 첫 화면은 문서용 `docs/index.html`보다 우선합니다. `server.py`도 자동 탐지하며 서버가 반환하는 화면·인증·JSON API는 기존 단일 호스트/앱 실행기를 통해 연결합니다. 정적 문서 화면을 실제 프로그램 성공으로 대신 표시하지 않습니다. 기존 일반 앱 업데이트는 검증 후 소스만 교체하며 플랫폼 빌드·재시작 없이 적용합니다. 새 앱/네이티브 모듈·연결 구조 변경에는 플랫폼 적용이 필요합니다. 원본 앱이 별도로 제공하는 업데이트 버튼은 그 앱의 자체 관리자 요구 조건을 유지하며 플랫폼 관리의 업데이트와는 별개입니다.

소스·기록·설정·번역 캐시: `runtime/projects/manage/`. 생성 모듈: Git 제외 `modules/external_*/`. 공통 Python/Node/추론 실행기를 재사용하며 Codex 개인 `.codex/skills`는 실행 의존성이 아닙니다. 내보내기는 위 실행 유형의 외부 앱을 대상으로 합니다. 금융·REA·Hermes는 설치 정보 → 개발자 상세의 **소스 ZIP 복사본 저장**에서 각 모듈과 필요한 호스트/UI 복사본·설치/실행 스크립트를 ZIP으로 저장합니다. 다른 모듈·원래 플랫폼·사용자 데이터·키·모델을 참조하는 배포본이 아닙니다. `설치.cmd`/`실행.cmd`와 `python run.py setup/check/run --port 8080`을 제공합니다. 기본 모듈 ZIP은 외부 앱 가져오기 ZIP과 다른 형식입니다. 다른 PC의 새 의존성 설치·실제 거래/추론 전체와 모든 외부 저장소의 자동 변환은 미확인입니다. 미지원 WPF·Misskey 봇을 성공 설치로 표시하지 않습니다.

## 확인

2026-10-19 프로젝트 업데이트 확인: 관련 회귀 51개·TypeScript·Vite 적용 통과. 실제 GitHub project-zero의 확인 시점 최신 커밋 `a49c576a4512`를 `project-zero/versions/version-3/source`에 설치했습니다. 원본 server:app의 HTML 화면·실제 /healthz 200·미인증 관리자 API 401·로그인 후 회사 대시보드·JavaScript 오류 0건을 확인했습니다. 업데이트 전후 플랫폼 PID는 27228로 동일했고 관리자 인증 정보도 유지됐습니다. project-zero/pluto-re의 기존 긴 ID 폴더는 저장소 이름으로 이동하고 기존 루트 폴더가 없어짐을 확인했습니다. Windows에서 디렉터리 rename이 거절되면 원본 전체를 먼저 복사·등록한 뒤 읽기 전용 파일을 포함한 이전 폴더를 정리하며, 정리 실패 시 위치를 남겨 완전 제거에 포함합니다. 검사 실행기는 development/scripts/verify_project_update.cjs, 결과는 runtime/projects/manage/verification/project-update.json과 project-zero-current-ui.png입니다. 원본 자체 업데이트 관리자를 실행한 검사나 실제 AI 모델 추론 검사는 아닙니다.

2026-10-18 메뉴 분류 변경: 백엔드/설치 회귀 검사 28개, 기존·신규 설치 앱/기본 엔진의 메뉴 분류 검사 3개, TypeScript·Vite 빌드 통과. 현재 8766의 GitHub 대메뉴·관리 링크와 AI 에이전트의 MCP 링크를 브라우저에서 확인했고 JavaScript 오류는 0건입니다. 이번 확인에서 새 외부 저장소 다운로드·설치나 모델 실행은 하지 않았습니다.

명령: `.venv/Scripts/python.exe -B -m unittest development.tests.test_project_packages development.tests.test_project_installer development.tests.test_project_lifecycle -q`, TypeScript, Vite. 개발 검사에서 사용자 모델을 임의로 실행하지 않습니다. `development/scripts/verify_project_agent.py --allow-local-model`은 사용자가 실제 모델 검사를 명시적으로 요청할 때만 수동 실행하는 별도 검사입니다.

현재 관련 검사 28개와 TypeScript가 통과했습니다. 새 검사는 원래 설치 폴더 제거 후 ZIP의 독립 웹 실행, ZIP 재설치 시 다운로드/모델 호출 없음, private wheel을 앱에만 설치한 뒤 CLI·ASGI에서 사용하고 제거, ZIP 경로 탈출 차단, 번역/미지원 설치에서 모델 자동 로드 없음까지 확인합니다. Git 제외 모듈의 등록 변경도 프론트와 API 변경으로 인식하는 회귀 검사를 포함합니다. 다른 PC의 의존성 설치, 모든 원본 앱의 독립 실행은 이 결과로 확인한 것이 아닙니다.

실제 8766 화면에서도 정적 검사 앱의 ZIP 다운로드 → 파일 설치 → 자동 메뉴/API 활성화 → 원본 iframe 표시 → 제거 → 파일/모듈/메뉴 소멸까지 통과했습니다. JavaScript 오류는 0건이며 사용자 모델은 실행하지 않았습니다. `development/scripts/verify_project_portability.cjs`, 결과 `runtime/projects/manage/verification/portable-ui.json`과 `portable-app.png`를 참고하세요. 이 검사에서 Git 제외 모듈의 API 갱신 누락과 설치 완료 이동 정보가 관리 화면 복귀를 방해하던 문제를 수정했습니다.

설치·분리·재연결·완전 제거·다른 프로젝트 보호·자동 MCP 등록 경로의 검사 22개가 통과했습니다. 실제 브라우저에서 상태 Drawer, 검사 전용 항목의 파일·레지스트리 영구 제거, MCP 기본 작업 화면과 JavaScript 오류 0건을 확인했습니다. 결과: `runtime/projects/manage/verification/workflow-ui.json`, `project-task.png`.

공개 morluto/rea 배포본 설치와 실제 stdio 도구 실행은 앞선 검사에서 확인했습니다. 이번 원본 Hermes 자동 등록에서는 도구 209개를 실제 발견했습니다. Ornith 검사 1회는 시간 제한에 걸렸고 재검사는 사용자 요청으로 중단한 뒤 모델을 내렸습니다. 자연어 요청부터 최종 분석 완료까지와 실제 모델 번역은 미확인입니다. 중단 기록은 `runtime/projects/manage/verification/agent-workflow-interrupted.json`에 있습니다. 도구 등록·검색을 분석 성공으로 취급하지 않습니다.

기본 모듈 소스 내보내기: backend/builtin_packages.py가 선택 모듈과 공통 코드 복사본만 수집하며 Git의 공개 프로그램 파일을 사용합니다(무시된 비밀 설정·런타임·실제 환경 제외). backend/standalone_runner.py는 독립 폴더 안에 환경을 설치하고 빌드/검사/실행합니다. 내보낸 뒤 의도적으로 수정한 소스는 실행을 막지 않으며 check에서 변경 목록을 표시합니다. Hermes는 공개 버전/해시 정보가 있을 때 공식 llama.cpp 실행기를 SHA-256 검증 후 해당 배포 폴더에 설치하며 모델을 자동 로드하지 않습니다.

2026-10-18 기본 모듈 독립 실행 확인: 금융·REA·Hermes ZIP을 각각 다른 임시 폴더로 풀고 원래 플랫폼 소스 import를 금지한 상태에서 전용 의존성 경로, 타입 검사·Vite 빌드, 단일 API·모듈/메뉴 카탈로그, Chromium 화면 표시와 JavaScript 오류 0건을 확인했습니다. REA 상태 API·Hermes 실제 worker 상태도 조회했으며 모델은 적재하지 않았습니다. 기존 설치 의존성의 경로 사본/NTFS 하드 링크로 검사했고 다른 PC에서 pip/npm을 새로 다운로드한 검사는 아닙니다. 임시 폴더와 서버는 정리했습니다. 실제 8766 관리 화면에서도 세 모듈의 독립 실행 소스 버튼과 금융 ZIP 다운로드를 확인했습니다. 결과는 runtime/projects/manage/verification/standalone-modules.json, 각 <모듈>-standalone.png, builtin-export-ui.png입니다. 실제 시세·학습·주문·컴퓨터 조작 전체를 이번 배포 검사에서 실행한 것은 아닙니다.

관련 설치/수명주기/외부 앱/기본 모듈 내보내기 회귀 31개 통과. Windows 독립 실행기의 한국어 오류 출력도 UTF-8로 통일했고 관련 9개를 추가 재확인했습니다. TypeScript·Vite 빌드와 8766 적용을 확인했습니다. 최종 금융·REA·Hermes ZIP 세 개를 실제 API로 생성하고 다운로드 Range 응답까지 확인했습니다. 새 PC 설치·실제 거래/추론 전체는 위 미확인 범위를 유지합니다.

## 설치·분리 화면의 현재 동작

화면은 설치한 앱과 기본 앱을 나누고 원본 화면/진입점 실행 확인을 실제 기록이 있을 때만 표시합니다. 원본 실행 환경이 로드되지 않은 모듈은 실행 버튼을 제공하지 않습니다. API 키 입력은 설치 필수가 아니며 원본 앱이 요구할 때만 설치 정보의 접힌 추가 환경 변수에서 설정합니다. 자동 분리는 주 동작이고 ZIP은 선택적인 전달용 복사본입니다.

앱 소스는 runtime/projects/manage/projects/<앱 이름>/, 연결 어댑터는 modules/external_<ID>/, 분리된 완성 폴더는 앱 소유 영역의 standalone/에 있습니다. 폴더 열기로 실제 위치를 확인합니다. 분리 자체는 사용자 데이터/비밀 설정을 보존하는 로컬 이동이며, 전달용 ZIP의 데이터/키 제외 정책과 다릅니다. 원본 모델은 사용자 지정 위치에 유지합니다.

실행 코드/진입점 없이 문서만 있는 저장소는 not_app(실행 앱 없는 자료)로 표시하며 모델 변환을 권하지 않습니다. 중단된 작업에 PID 정보가 없으면 영구 진행 상태로 남기지 않습니다. 잔재 정리는 이전 내보내기 ZIP과 오래된 가져오기 임시 파일만 원래 상대 경로를 유지해 휴지통으로 옮기며 설치 소스·데이터·모델은 정리 대상이 아닙니다.

현재 로컬 분리 확인(2026-10-18): 회귀 검사 44개 통과. 실제 공개 MDN 앱의 다운로드·원본 UI·선택 환경 설정·자동 분리·독립 실행·재연결·완전 제거를 확인했습니다. 기본 REA의 실제 모듈/전용 환경/소유 데이터를 이동해 독립 API·브라우저·상태 조회와 원래 위치 복원을 확인했습니다. 실행기는 development/scripts/verify_project_detachment.cjs와 verify_builtin_detachment.py, 결과는 runtime/projects/manage/verification/{detachment-ui,builtin-detachment}.json입니다. 모델 추론·실제 거래는 실행하지 않았고 다른 PC 새 설치는 미확인입니다. 금융·Hermes의 새 로컬 이동 흐름 전체는 이번 실제 REA 검증과 구분합니다.

Windows 원본 설치기: windows/install*.ps1·scripts/install*.ps1·install.ps1의 단일 진입점을 탐지하면 PowerShell AST로 문법·필수 값·기본 값·선택 값·스위치를 읽고 한글 설치 화면을 자동 연결합니다. 탐지/화면 등록에서는 원본을 실행하지 않습니다. 설치 화면에서 사용자가 실행해야 다운로드·대상 폴더 변경이 시작되며 실행 로그·중지·실패를 같은 화면에 표시합니다. 문서와 분석 도구가 함께 있는 저장소를 문서만 있는 저장소로 오분류하지 않습니다. 원본 웹 UI가 없는 Windows 설치기는 웹 UI 연결이 아니라 공통 설치 화면을 사용하는 유형입니다. API는 projects/setup(GET/POST), setup/status, setup/stop이며 분리 ZIP은 원본 Windows 설치 스크립트와 실행 진입점을 포함합니다. 분리 후에는 원본 PowerShell 옵션으로 실행하며 플랫폼 설치 폼까지 별도 웹앱으로 복제하지 않습니다.

2026-10-18 Windows 설치기 확인: 관련 회귀 검사 32개·TypeScript·Vite 통과. 기존 pluto-re를 모델 없이 원본 powershell 설치기 유형으로 재등록하고 PC/390px 설치 옵션 UI를 확인했습니다. 실제 원본 스크립트를 빈 검사 폴더 대상으로 호출해 StarCraft.exe 사전 조건 실패와 로그 표시를 확인했으며 다운로드/게임 설치는 시작하지 않았습니다. 정상 실행은 별도 무해한 PowerShell 검사 설치기로 옵션·선택·스위치와 문자열 인수 전달을 확인했습니다. 실제 브루드워 1.16.1 경로의 전체 다운로드·Pluto 실행은 미확인입니다. 결과는 runtime/projects/manage/verification/windows-installer-ui.json, 실행기는 development/scripts/verify_windows_installer.cjs입니다.

설치 폴더 규칙: 모든 GitHub 앱은 프로젝트 관리 소속 runtime/projects/manage/projects/<앱 이름>/ 아래에 소스 버전·전용 패키지·실행 자료를 둡니다. 이 부모 폴더를 project_folder로 공통 제공하고 폴더 열기도 해당 위치를 엽니다. Windows 설치기의 InstallDir/InstallPath/Destination/TargetDir 등 설치 대상 옵션은 이 앱의 application/으로 자동 지정해 입력칸을 숨깁니다. 기존 게임처럼 원본이 이미 있어야 하는 StarCraftDir 등은 설치 대상과 구분하며 빈 자동 생성 폴더로 대체하지 않습니다.

폴더 자동 관리 확인(2026-10-18): 관련 회귀 검사 40개·TypeScript/Vite 통과. 원본 검사 설치기에 설치 경로를 입력하지 않고 앱의 application/ 내부 파일 생성까지 확인했습니다. 기존 게임 입력을 설치 대상과 구분하는 검사도 포함합니다. 실제 pluto-re의 앱 소유 폴더 표시와 PC/390px 화면·오류 표시를 확인했고 JavaScript 오류/가로 넘침은 없었습니다. 기존 게임 파일 없이 Pluto 전체를 설치한 것은 아닙니다.

UI 없는 CLI의 자동 화면: cli_schema.py가 원본 argparse 코드를 AST로 읽어 하위 명령·필수 값·숫자·선택·스위치·목록을 추출하고 공통 CliApp/GeneratedFieldInput이 런타임에 화면을 구성합니다. 분석 때문에 원본을 import/실행하거나 사용자 모델을 호출하지 않습니다. main.py 등과 README가 직접 가리키는 Python 도구도 자동 탐지합니다. 앱마다 React 화면/HTML을 생성하지 않으며 기존 웹 UI는 우선 유지합니다.

API: projects/interface(GET), projects/action(POST). 실행할 명령은 서버가 다시 추출한 원본 기능 ID/필드로 검증하고 기존 전용 패키지 실행기를 사용합니다. 기존 설치 앱도 새 공통 화면을 사용합니다. PowerShell 설치기가 있는 저장소의 Python 도구는 프로젝트 기능 탭에 자동 표시합니다. 원본 함수 진입점/스크립트와 분리 ZIP 실행을 유지합니다. 자동 추출하지 못한 원본 CLI는 고급 도움말/기존 실행을 보존하며 추출 성공으로 표시하지 않습니다. argparse 동적 옵션/임의 프레임워크 전체의 의미를 추론하는 범용 변환이 완성된 것은 아닙니다.

2026-10-18 자동 UI 확인: 관련 회귀 35개·TypeScript 통과. 원본 UI 없는 일반 argparse 검사 앱을 자동 탐지해 기존 설치 경로로 등록했고 원본 2개 명령의 필수/숫자/선택/스위치/목록 화면과 실제 실행·결과 파일 생성을 확인했습니다. 앱 전용 프론트 파일은 자동 등록용 register.ts 하나뿐이었으며 별도 React UI는 만들지 않았습니다. 1440px/390px 가로 넘침·JavaScript 오류는 없었고 사용자 모델은 사용하지 않았습니다. 검사 앱/임시 소스는 제거했습니다. 실제 GitHub 다운로드 검사는 아닌 로컬 검사 소스의 공통 설치/메뉴/화면 검증입니다. 결과 runtime/projects/manage/verification/automatic-ui.json, 실행 development/scripts/verify_automatic_ui.cjs. 독립 ZIP의 원본 CLI check/run과 기존 웹 UI 우선 유지도 회귀에 포함합니다.

기존 pluto-re도 재설치/전용 UI 수정 없이 README의 analysis/weights.py에서 1개 기능 화면을 자동 추출해 프로젝트 기능 탭에 표시합니다. 실제 브라우저에서 입력/검사 옵션과 JavaScript 오류 없음을 확인했으며 원본 가중치 분석 실행은 하지 않았습니다. 화면은 runtime/projects/manage/verification/pluto-generated-tools.png입니다.

## 원본 앱 대화의 Hermes 하네스 연결

지원하는 원본 FastAPI 앱의 대화/업무 응답을 Hermes 하네스로 연결할 수 있습니다. 설치 정보 → 대화 실행 엔진에서 선택하며, 원본 UI·승인·DB 기록을 유지합니다. 앱 상단에서 실제 도구 내역·승인·질문·중지를 처리합니다. 설정은 업데이트에도 유지하며 원본 소스를 수정하거나 Hermes를 복제하지 않습니다. 현재 지원 규격·단독 실행 경계·API·검사는 [백엔드 안내](backend/README.md#원본-앱-대화의-hermes-하네스-연결)를 봅니다.

2026-10-19 하네스 적용 확인: 관련 회귀 58개·TypeScript·Vite 통과. 실제 project-zero의 기존 대화창 → Hermes 도구 실행/파일 읽기 → 원래 대화 기록·화면 응답을 확인했고 JavaScript 오류는 없었습니다. 지원 함수 규격, 초기 실패 수정과 실제 검증 한계는 위 백엔드 안내에 기록했습니다.

2026-10-19 Project Zero 대화·업무 호환 수정: 현재 요청/과거 기록 분리, JSON 계획과 실제 직원 도구 실행 분리, 부정문·초안 수정 오판과 모델 오류 시 임의 업무 생성 방지, 원본 로컬 자동 로그인 전달을 적용했습니다. 업무 회귀 36개(격리 DB/모의 모델)와 플랫폼 회귀 57개, 실제 원본 UI의 인사·CTO 파일 읽기/DB 결과 저장을 확인했습니다. 원본 앱 소스는 변경하지 않았습니다. 사용 경로·검증 기록·모델 출력 품질 한계는 [백엔드 안내](backend/README.md#project-zero-업무대화-호환)를 따릅니다.

현재 Project Zero 경영실은 대화/회의/업무/사업안으로 구분합니다. 원본 UI는 별도로 유지하고 실제 사업 승인과 작업 기록은 원본 API/DB를 사용합니다. 회의·사업 검토의 기본 맥락을 분리하고 공유 기억 선택 스위치를 제공합니다. 격리 업무/호환 41개·플랫폼 회귀 60개와 실제 전문가 5명+CEO의 6세션 회의를 확인했습니다. UI 및 모델 검증의 구분과 한계는 [경영실 안내](frontend/project_zero/README.md)와 [백엔드 안내](backend/README.md)를 따릅니다.
