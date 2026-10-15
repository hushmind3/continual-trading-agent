# Hermes

Platform submenu: `AI Agent / Hermes`, frontend `#ai_agent/Hermes`.

| Folder | Responsibility |
| --- | --- |
| engine/ | Imported upstream engine and common dependencies; isolated Python worker and IPC |
| chat/ | Start, progress, streaming output and stop |
| models/ | OpenAI-compatible model connection and local model process |
| sessions/ | Upstream SessionDB history and session management |
| mcp/ | Upstream MCP server configuration and tool discovery |
| skills/ | Upstream skill catalog and skill content |

`manager.py` collects feature routers. It is the only submenu module imported by the AI Agent coordinator.

The original checkout is not a runtime dependency. Upstream Python sources are under `engine/upstream/`; source hashes and deliberate bootstrap changes are recorded in `engine/provenance.json`. The original MIT license is retained. CLI/package-update launchers are not executed. Configuration, credentials, sessions and logs live under project `runtime/ai_agent/Hermes/` and are excluded from Git.

Python: use the already installed Python 3.14 through `.venv/hermes/`; do not change the finance Python environment. Install selected dependencies with `uv pip install --python .venv/hermes/Scripts/python.exe -r backend/ai_agent/Hermes/engine/requirements.txt`. No model is downloaded or loaded automatically.

Complete dependency/desktop-driver setup: `.venv\Scripts\python.exe -I -X utf8 backend/ai_agent/Hermes/engine/setup.py`. This reuses installed Python 3.14, and verifies the desktop driver's archive against the SHA-256 in the copied upstream PM lock. The original source folder is never consulted by setup or execution.

Source selection excludes the standalone CLI, TUI gateway, messaging adapter entrypoints and upstream tests/evaluations. Common config/session/approval/PM metadata helpers still required by selected tools remain. The ACP edit-approval middleware is retained because the engine requires it even outside ACP sessions; no ACP client is launched. The system does not run the upstream package updater. Imported skills may describe optional tools that need separate credentials or software; merely listing or reading them does not execute them.

컴퓨터·브라우저: 모델 탭에서 사용할 기능을 선택한 뒤 대화에서 요청합니다. 클릭·입력 승인 요청은 대화 화면에서 허용/거절합니다. 로컬 텍스트 GGUF는 AX 접근성 텍스트로 작업하며, 화면 이미지 이해가 필요한 앱은 별도 비전 모델/프로젝터가 필요합니다. 설치 시 루트 npm ci로 공유 브라우저 의존성도 설치합니다. 실제 동작 검사는 development/tests/test_hermes_live_tools.py에 있으며 HERMES_LIVE_TOOLS=1일 때만 모델·검사 창을 실행합니다.
