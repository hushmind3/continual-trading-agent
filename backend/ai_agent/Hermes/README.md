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
