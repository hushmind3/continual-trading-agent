# Hermes 백엔드

용도: 이식 엔진·전용 실행 환경·기능 API와 설정 소유를 안내합니다.

런타임 소유 경로는 `runtime/ai_agent/Hermes/`입니다. 대화 DB·공통 설정은 원본 엔진이 공유하며, 스킬은 `skills/`, 도구 실행기는 `tools/`, 검사 자료는 `verification/`에 둡니다. 이식 검사 임시 파일은 `verification/port/run-…/`에서만 만들고 정상 종료와 준비 실패 모두 정리합니다. 실행 충돌을 막기 위한 임시 실행 ID 외에 런타임 최상위에 무작위 이름의 폴더를 만들지 않습니다. 대화·세션·MCP마다 별도 DB와 설정 복사본을 만드는 구조는 아닙니다.

메뉴 계층: AI 에이전트(대메뉴) → Hermes(중메뉴) → 대화·모델·작업 환경·MCP·스킬·시스템 프롬프트(소메뉴). 대화 주소는 `#ai_agent/Hermes`입니다.

| Folder | Responsibility |
| --- | --- |
| engine/ | Imported upstream engine and common dependencies; isolated Python worker and IPC |
| chat/ | Start, progress, streaming output and stop |
| models/ | OpenAI-compatible model connection and local model process |
| sessions/ | Upstream SessionDB history and session management |
| mcp/ | Upstream MCP server configuration and tool discovery |
| skills/ | Upstream skill catalog and skill content |

`module.json`의 backend 항목이 `manager.py`를 자동 등록합니다. manager가 기능별 router를 취합해 전체 메뉴의 단일 `/api`로 연결하고, 실제 AIAgent는 모듈 전용 Python worker에서 실행합니다.

The original checkout is not a runtime dependency. Upstream Python sources are under `engine/upstream/`; source hashes and deliberate bootstrap changes are recorded in `engine/provenance.json`. The original MIT license is retained. CLI/package-update launchers are not executed. Configuration, credentials, sessions and logs live under project `runtime/ai_agent/Hermes/` and are excluded from Git.

Python: use the already installed Python 3.14 through `modules/hermes/.venv/`; do not change the finance Python environment. Install selected dependencies with `uv pip install --python modules/hermes/.venv/Scripts/python.exe -r modules/hermes/backend/engine/requirements.txt`. No model is downloaded or loaded automatically.

Complete dependency/desktop-driver setup: `.venv\Scripts\python.exe -I -X utf8 modules/hermes/backend/engine/setup.py`. This reuses installed Python 3.14, and verifies the desktop driver's archive against the SHA-256 in the copied upstream PM lock. The original source folder is never consulted by setup or execution.

Source selection excludes the standalone CLI, TUI gateway, messaging adapter entrypoints and upstream tests/evaluations. Common config/session/approval/PM metadata helpers still required by selected tools remain. The ACP edit-approval middleware is retained because the engine requires it even outside ACP sessions; no ACP client is launched. The system does not run the upstream package updater. Imported skills may describe optional tools that need separate credentials or software; merely listing or reading them does not execute them.

컴퓨터·브라우저: 작업 환경 소메뉴에서 사용할 도구를 선택한 뒤 대화에서 요청합니다. 클릭·입력 승인 요청은 대화 화면에서 허용/거절합니다. 로컬 텍스트 GGUF는 AX 접근성 텍스트로 작업하며, 화면 이미지 이해가 필요한 앱은 별도 비전 모델/프로젝터가 필요합니다. 브라우저 Node 패키지는 modules/hermes/backend/engine/browser/node_modules에 설치합니다. 루트 node_modules를 참조하지 않습니다. 실제 동작 검사는 development/tests/test_hermes_live_tools.py에 있으며 HERMES_LIVE_TOOLS=1일 때만 모델·검사 창을 실행합니다.

시스템 프롬프트: 프론트 설정 → 시스템 프롬프트에서 저장합니다. `platform-settings.json`의 system_prompt를 원본 AIAgent의 ephemeral_system_prompt 인자에 추가하며, 기본 도구 안내는 유지합니다. 다음 대화 요청부터 적용하고 빈 문자열로 저장하면 사용자 추가 지침을 해제합니다.

프로젝트 설치기의 자동 변환 요청은 실행별 workspace를 전달할 수 있습니다. worker는 실제 존재하는 폴더만 받아 해당 실행의 작업 경로에 적용합니다. 저장된 기본 작업 폴더는 바꾸지 않으며 모델 준비·승인·중지는 기존 엔진 경로를 유지합니다. 이번 설치기 변경에서 실제 모델을 통한 자동 변환까지 확인한 것은 아닙니다.

artifacts/는 대화 결과 문서 미리보기를 단일 API에 등록합니다. Markdown 링크·인라인 문서 경로·성공한 파일 쓰기의 결과 파일을 프론트에서 열 수 있습니다. 읽기 전용 실행 권한은 시스템 프롬프트 문장과 별도 설정이며 대화 입력창의 읽기 모드 스위치로 다음 요청부터 적용됩니다.

2026-10-16 확인: 금융·REA 회귀 110개, Hermes 권한·재시작·문서 검사 11개 통과. TypeScript·Vite 빌드 및 서버 적용 완료. 실제 오류 보고서 문서 API 응답 확인. 실제 GGUF 추론은 이번 검증에서 실행하지 않았습니다.

현재 분리 범위와 검증은 [모듈 안내](../../README.md), 현재 대화 제어는 [대화 README](../frontend/chat/README.md)를 따릅니다.
