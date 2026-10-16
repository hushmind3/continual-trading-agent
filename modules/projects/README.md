# 프로젝트 설치·관리 안내

GitHub 주소/검색 결과에서 **설치**를 누르면 실행 유형 탐지 → 의존성 준비 → 실제 실행 확인 → 화면·메뉴 연결을 자동 처리합니다. 표준 실행 유형의 설치에는 LLM 추론이 필요하지 않습니다. 알려지지 않은 구조의 어댑터 생성과 선택적 한국어 번역은 모델을 별도로 사용하며, 설치 성공을 보장하는 대체 수단으로 표시하지 않습니다.

## 구현과 연결

- `backend/adapters.py`, `node_mcp.py`: 정적 HTML·Vite·FastAPI·Python CLI·Node stdio MCP·플랫폼 모듈 탐지. MCP는 원본 manifest의 정확한 npm 버전과 배포 저장소를 확인합니다.
- `backend/installer.py`: 저장된 설치 작업·검증·게시. MCP는 `agent_tasks.link_when_idle`까지 실행한 뒤 활성화합니다. 기존 에이전트 작업 중이면 완료를 기다리며 취소할 수 있습니다.
- `backend/agent_tasks.py`: 저장소별 코드를 추가하지 않는 에이전트 연결·자연어 작업 시작. 원본 Hermes의 `mcp/project`와 `chat`을 호출합니다. 연결된 실제 도구 이름을 요청에 맞춰 안내하며 결과를 지어내지 않도록 지시합니다.
- `backend/runtime.py`, `app_worker.py`, `mcp_worker.py`: 원본 웹 UI·ASGI·MCP 실행. 메뉴별 HTTP 서버를 추가하지 않습니다.
- `backend/lifecycle.py`: 분리·재연결·완전 제거. `backend/handlers.py` → `manager.py` → 플랫폼 총괄의 단일 `/api` 구조입니다.
- `frontend/ProjectApp.tsx`: 원본 UI가 있으면 표시하고, MCP에는 `ProjectTask.tsx`의 대상·요청·작업 시작 화면을 자동 선택합니다. 수동 도구/JSON은 개발자 상세에만 있습니다. 다른 종류는 기존 공통 실행/기능 UI를 사용합니다.
- `frontend/ProjectSettings.tsx`: 즉시 열리는 공통 Drawer로 상태·환경 설정·설치 로그를 표시합니다.
- `backend/localization.py`, `project_language.js`, `frontend/useKorean.ts`: 로컬 모델 번역 캐시. 검색 설명과 지원 웹앱의 표시 문자열을 한국어로 변환하고 원본 소스는 바꾸지 않습니다. 번역이 없어도 설치할 수 있습니다. 코드·식별자·제품명은 보존하며 임의의 네이티브 앱·모든 CSP/동적 UI까지 한글화한다고 보장하지 않습니다.

## 사용과 데이터

메뉴: 프로젝트 → 프로젝트 관리 → GitHub에서 추가/설치된 프로젝트. API: `projects/install`, `retry`, `detach`, `reconnect`, `remove`, `detail`, `settings`, `agent/connect`, `agent/start`, `localize`. 검색은 30개씩 더 보기·정렬을 제공합니다.

- **분리:** 연결 모듈을 해당 프로젝트 런타임의 `detached/`에 보관하고 메뉴·MCP 연결을 해제합니다. 소스·설정·기록은 유지합니다.
- **다시 연결:** 저장된 모듈을 재사용합니다. 다운로드·AI 변환을 다시 실행하지 않습니다. 예전 휴지통 방식의 분리본도 찾습니다.
- **제거:** 사용자의 완전 삭제 요청에 따라 해당 외부 프로젝트의 모듈·설치 파일·설정·기록을 영구 삭제합니다. 공유 실행기·원본 모델·다른 프로젝트는 삭제하지 않습니다. 일부 파일이 잠기면 제거 실패로 남겨 재시도하게 합니다. 과거 제거에서 휴지통으로 옮겨진 별도 항목이 자동 소멸한 것은 아닙니다.

기본 금융·REA·Hermes는 플랫폼 포함 모듈이며 이 외부 설치기의 제거 대상으로 취급하지 않습니다. 특히 기존 REA와 설치한 morluto/rea는 별도 프로젝트입니다.

소스·기록·설정·번역 캐시: `runtime/projects/manage/`. 생성 모듈: Git 제외 `modules/external_*/`. 공통 Python/Node/추론 실행기를 재사용하며 Codex 개인 `.codex/skills`는 실행 의존성이 아닙니다. 독립 배포 패키지 생성은 미완료입니다. 미지원 WPF·Misskey 봇을 성공 설치로 표시하지 않습니다.

## 확인

명령: `.venv/Scripts/python.exe -B -m unittest development.tests.test_project_installer development.tests.test_project_lifecycle -q`, TypeScript, Vite. 개발 검사에서 사용자 모델을 임의로 실행하지 않습니다. `development/scripts/verify_project_agent.py --allow-local-model`은 사용자가 실제 모델 검사를 명시적으로 요청할 때만 수동 실행하는 별도 검사입니다.

설치·분리·재연결·완전 제거·다른 프로젝트 보호·자동 MCP 등록 경로의 검사 22개가 통과했습니다. 실제 브라우저에서 상태 Drawer, 검사 전용 항목의 파일·레지스트리 영구 제거, MCP 기본 작업 화면과 JavaScript 오류 0건을 확인했습니다. 결과: `runtime/projects/manage/verification/workflow-ui.json`, `project-task.png`.

공개 morluto/rea 배포본 설치와 실제 stdio 도구 실행은 앞선 검사에서 확인했습니다. 이번 원본 Hermes 자동 등록에서는 도구 209개를 실제 발견했습니다. Ornith 검사 1회는 시간 제한에 걸렸고 재검사는 사용자 요청으로 중단한 뒤 모델을 내렸습니다. 자연어 요청부터 최종 분석 완료까지와 실제 모델 번역은 미확인입니다. 중단 기록은 `runtime/projects/manage/verification/agent-workflow-interrupted.json`에 있습니다. 도구 등록·검색을 분석 성공으로 취급하지 않습니다.
