# Engine

`upstream/` contains copied upstream implementation, not a replacement agent loop. `provenance.json` records origins and bootstrap changes. `worker.py` calls upstream AIAgent, SessionDB, tool registry, MCP and skills in an isolated process. `bridge.py` provides JSON-line IPC to the existing FastAPI process; no additional public gateway is started.

Python dependencies belong to `.venv/hermes/`; runtime state belongs to `runtime/ai_agent/Hermes/`. All runtime paths resolve from this project. The original checkout must not appear on PYTHONPATH or be used as a symlink target.

브라우저 실행기는 root npm workspace의 agent-browser 0.26.0이며 설치된 Chrome/Edge를 재사용합니다. 기본 native 설정에서 browser.backend=off는 browser-use CLI만 끄고 원본 agent-browser 도구를 사용한다는 뜻입니다. 채팅은 원본 interactive approval context를 사용해 프론트 허용/거절에 연결합니다. AX 캡처의 전체 텍스트를 제한 길이로 보존하는 로컬 패치는 provider-provenance.json에 기록합니다.
