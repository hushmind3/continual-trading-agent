# Engine

`upstream/` contains copied upstream implementation, not a replacement agent loop. `provenance.json` records origins and bootstrap changes. `worker.py` calls upstream AIAgent, SessionDB, tool registry, MCP and skills in an isolated process. `bridge.py` provides JSON-line IPC to the existing FastAPI process; no additional public gateway is started.

Python dependencies belong to `.venv/hermes/`; runtime state belongs to `runtime/ai_agent/Hermes/`. All runtime paths resolve from this project. The original checkout must not appear on PYTHONPATH or be used as a symlink target.
