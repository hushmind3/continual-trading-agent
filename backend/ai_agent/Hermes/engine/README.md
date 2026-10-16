# Engine

`upstream/` contains copied upstream implementation, not a replacement agent loop. `provenance.json` records origins and bootstrap changes. `worker.py` calls upstream AIAgent, SessionDB, tool registry, MCP and skills in an isolated process. `bridge.py` provides JSON-line IPC to the existing FastAPI process; no additional public gateway is started.

Python dependencies belong to `.venv/hermes/`; runtime state belongs to `runtime/ai_agent/Hermes/`. All runtime paths resolve from this project. The original checkout must not appear on PYTHONPATH or be used as a symlink target.

브라우저 실행기는 root npm workspace의 agent-browser 0.26.0이며 설치된 Chrome/Edge를 재사용합니다. 기본 native 설정에서 browser.backend=off는 browser-use CLI만 끄고 원본 agent-browser 도구를 사용한다는 뜻입니다. 채팅은 원본 interactive approval context를 사용해 프론트 허용/거절에 연결합니다. AX 캡처의 전체 텍스트를 제한 길이로 보존하는 로컬 패치는 provider-provenance.json에 기록합니다.

서버 재시작 전 기존 worker 상태만 확인하며 작업·중지 처리·모델 로딩·MCP 설치 중에는 재시작을 차단합니다. 준비 승인 시 새 요청을 차단한 뒤 상태를 재확인하고 IPC 쓰기와 직렬화해 시작/재시작 경합을 막습니다. 상태 확인 실패도 재시작 허용으로 처리하지 않습니다.
