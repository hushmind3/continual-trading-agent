# 프로젝트 설치·관리 안내

용도: GitHub·앱 파일에서 설치한 프로그램의 실행과 분리·재연결·완전 제거를 담당합니다.

**설치**를 누르면 실행 유형 탐지 → 의존성 준비 → 실제 실행 확인 → 화면·메뉴 연결을 자동 처리합니다. 설치 오류가 나도 모델을 임의로 불러오지 않습니다. 미지원 구조의 모델 자동 변환은 사용자가 설치 화면이나 앱 설정에서 켠 경우에만 실행합니다. 한국어 번역도 이미 준비된 유휴 모델만 사용합니다.

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

- **분리:** 연결 모듈을 해당 프로젝트 런타임의 `detached/`에 보관하고 메뉴·MCP 연결을 해제합니다. 소스·설정·기록은 유지합니다.
- **다시 연결:** 저장된 모듈을 재사용합니다. 다운로드·AI 변환을 다시 실행하지 않습니다. 예전 휴지통 방식의 분리본도 찾습니다.
- **내보내기:** 정적/Vite/FastAPI/Python CLI/Node MCP 앱의 소스·실행 설명·독립 실행기를 ZIP으로 저장합니다. 다른 폴더에서 `python run.py setup`, `check`, `run`으로 원본 기능을 실행하거나 **앱 파일에서 설치**로 가져옵니다. 모델·DB·로그·data/runtime 폴더·비밀 설정은 포함하지 않으며 필요한 외부 서비스/키는 새 환경에 설정해야 합니다. 가져오기는 원본 설치/검증 경로를 재사용합니다. ZIP 32 MiB·소스 128 MiB 한도, 파일 해시·경로·중복 검사, 가져오기 임시 파일 정리를 적용합니다.
- **제거:** 사용자의 완전 삭제 요청에 따라 해당 외부 프로젝트의 모듈·설치 파일·설정·기록을 영구 삭제합니다. 공유 실행기·원본 모델·다른 프로젝트는 삭제하지 않습니다. 일부 파일이 잠기면 제거 실패로 남겨 재시도하게 합니다. 과거 제거에서 휴지통으로 옮겨진 별도 항목이 자동 소멸한 것은 아닙니다.

기본 금융·REA·Hermes도 독립 실행 소스를 내보낼 수 있습니다. 기존 설치본은 이 외부 설치기의 완전 제거 대상으로 취급하지 않습니다. 특히 기존 REA와 설치한 morluto/rea는 별도 프로젝트입니다.

소스·기록·설정·번역 캐시: `runtime/projects/manage/`. 생성 모듈: Git 제외 `modules/external_*/`. 공통 Python/Node/추론 실행기를 재사용하며 Codex 개인 `.codex/skills`는 실행 의존성이 아닙니다. 내보내기는 위 실행 유형의 외부 앱을 대상으로 합니다. 금융·REA·Hermes는 설치된 프로젝트의 **독립 실행 소스** 버튼에서 각 모듈과 필요한 호스트/UI 복사본·설치/실행 스크립트를 ZIP으로 저장합니다. 다른 모듈·원래 플랫폼·사용자 데이터·키·모델을 참조하는 배포본이 아닙니다. `설치.cmd`/`실행.cmd`와 `python run.py setup/check/run --port 8080`을 제공합니다. 기본 모듈 ZIP은 외부 앱 가져오기 ZIP과 다른 형식입니다. 다른 PC의 새 의존성 설치·실제 거래/추론 전체와 모든 외부 저장소의 자동 변환은 미확인입니다. 미지원 WPF·Misskey 봇을 성공 설치로 표시하지 않습니다.

## 확인

2026-10-18 메뉴 분류 변경: 백엔드/설치 회귀 검사 28개, 기존·신규 설치 앱/기본 엔진의 메뉴 분류 검사 3개, TypeScript·Vite 빌드 통과. 현재 8766의 GitHub 대메뉴·관리 링크와 AI 에이전트의 MCP 링크를 브라우저에서 확인했고 JavaScript 오류는 0건입니다. 이번 확인에서 새 외부 저장소 다운로드·설치나 모델 실행은 하지 않았습니다.

명령: `.venv/Scripts/python.exe -B -m unittest development.tests.test_project_packages development.tests.test_project_installer development.tests.test_project_lifecycle -q`, TypeScript, Vite. 개발 검사에서 사용자 모델을 임의로 실행하지 않습니다. `development/scripts/verify_project_agent.py --allow-local-model`은 사용자가 실제 모델 검사를 명시적으로 요청할 때만 수동 실행하는 별도 검사입니다.

현재 관련 검사 28개와 TypeScript가 통과했습니다. 새 검사는 원래 설치 폴더 제거 후 ZIP의 독립 웹 실행, ZIP 재설치 시 다운로드/모델 호출 없음, private wheel을 앱에만 설치한 뒤 CLI·ASGI에서 사용하고 제거, ZIP 경로 탈출 차단, 번역/미지원 설치에서 모델 자동 로드 없음까지 확인합니다. Git 제외 모듈의 등록 변경도 프론트와 API 변경으로 인식하는 회귀 검사를 포함합니다. 다른 PC의 의존성 설치, 모든 원본 앱의 독립 실행은 이 결과로 확인한 것이 아닙니다.

실제 8766 화면에서도 정적 검사 앱의 ZIP 다운로드 → 파일 설치 → 자동 메뉴/API 활성화 → 원본 iframe 표시 → 제거 → 파일/모듈/메뉴 소멸까지 통과했습니다. JavaScript 오류는 0건이며 사용자 모델은 실행하지 않았습니다. `development/scripts/verify_project_portability.cjs`, 결과 `runtime/projects/manage/verification/portable-ui.json`과 `portable-app.png`를 참고하세요. 이 검사에서 Git 제외 모듈의 API 갱신 누락과 설치 완료 이동 정보가 관리 화면 복귀를 방해하던 문제를 수정했습니다.

설치·분리·재연결·완전 제거·다른 프로젝트 보호·자동 MCP 등록 경로의 검사 22개가 통과했습니다. 실제 브라우저에서 상태 Drawer, 검사 전용 항목의 파일·레지스트리 영구 제거, MCP 기본 작업 화면과 JavaScript 오류 0건을 확인했습니다. 결과: `runtime/projects/manage/verification/workflow-ui.json`, `project-task.png`.

공개 morluto/rea 배포본 설치와 실제 stdio 도구 실행은 앞선 검사에서 확인했습니다. 이번 원본 Hermes 자동 등록에서는 도구 209개를 실제 발견했습니다. Ornith 검사 1회는 시간 제한에 걸렸고 재검사는 사용자 요청으로 중단한 뒤 모델을 내렸습니다. 자연어 요청부터 최종 분석 완료까지와 실제 모델 번역은 미확인입니다. 중단 기록은 `runtime/projects/manage/verification/agent-workflow-interrupted.json`에 있습니다. 도구 등록·검색을 분석 성공으로 취급하지 않습니다.

기본 모듈 소스 내보내기: backend/builtin_packages.py가 선택 모듈과 공통 코드 복사본만 수집하며 Git의 공개 프로그램 파일을 사용합니다(무시된 비밀 설정·런타임·실제 환경 제외). backend/standalone_runner.py는 독립 폴더 안에 환경을 설치하고 빌드/검사/실행합니다. 내보낸 뒤 의도적으로 수정한 소스는 실행을 막지 않으며 check에서 변경 목록을 표시합니다. Hermes는 공개 버전/해시 정보가 있을 때 공식 llama.cpp 실행기를 SHA-256 검증 후 해당 배포 폴더에 설치하며 모델을 자동 로드하지 않습니다.

2026-10-18 기본 모듈 독립 실행 확인: 금융·REA·Hermes ZIP을 각각 다른 임시 폴더로 풀고 원래 플랫폼 소스 import를 금지한 상태에서 전용 의존성 경로, 타입 검사·Vite 빌드, 단일 API·모듈/메뉴 카탈로그, Chromium 화면 표시와 JavaScript 오류 0건을 확인했습니다. REA 상태 API·Hermes 실제 worker 상태도 조회했으며 모델은 적재하지 않았습니다. 기존 설치 의존성의 경로 사본/NTFS 하드 링크로 검사했고 다른 PC에서 pip/npm을 새로 다운로드한 검사는 아닙니다. 임시 폴더와 서버는 정리했습니다. 실제 8766 관리 화면에서도 세 모듈의 독립 실행 소스 버튼과 금융 ZIP 다운로드를 확인했습니다. 결과는 runtime/projects/manage/verification/standalone-modules.json, 각 <모듈>-standalone.png, builtin-export-ui.png입니다. 실제 시세·학습·주문·컴퓨터 조작 전체를 이번 배포 검사에서 실행한 것은 아닙니다.

관련 설치/수명주기/외부 앱/기본 모듈 내보내기 회귀 31개 통과. Windows 독립 실행기의 한국어 오류 출력도 UTF-8로 통일했고 관련 9개를 추가 재확인했습니다. TypeScript·Vite 빌드와 8766 적용을 확인했습니다. 최종 금융·REA·Hermes ZIP 세 개를 실제 API로 생성하고 다운로드 Range 응답까지 확인했습니다. 새 PC 설치·실제 거래/추론 전체는 위 미확인 범위를 유지합니다.
