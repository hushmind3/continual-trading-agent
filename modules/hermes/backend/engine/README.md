# Engine

`upstream/` contains copied upstream implementation, not a replacement agent loop. `provenance.json` records origins and bootstrap changes. `worker.py` calls upstream AIAgent, SessionDB, tool registry, MCP and skills in an isolated process. `bridge.py` provides JSON-line IPC to the existing FastAPI process; no additional public gateway is started.

Python dependencies belong to `.venv/hermes/`; runtime state belongs to `runtime/ai_agent/Hermes/`. All runtime paths resolve from this project. The original checkout must not appear on PYTHONPATH or be used as a symlink target.

프로젝트 자동 연결은 `mcp/project` 명령을 `../mcp/project_links.py`로 전달합니다. 다른 MCP 설정을 보존하면서 프로젝트 전용 서버만 추가·해제하며, 원본 discovery와 도구 등록 결과를 확인합니다. 로컬 모델 로더는 설치된 llama.cpp의 `--n-gpu-layers auto`를 사용합니다. 기존 999 고정값이 자동 메모리 맞춤을 막아 Vulkan KV 캐시 할당에 실패한 것을 확인했으며, 문맥 크기는 사용자/원본 설정을 유지하고 GPU 계층만 가용 VRAM에 맞춥니다.

브라우저 실행기는 root npm workspace의 agent-browser 0.26.0이며 설치된 Chrome/Edge를 재사용합니다. 기본 native 설정에서 browser.backend=off는 browser-use CLI만 끄고 원본 agent-browser 도구를 사용한다는 뜻입니다. 채팅은 원본 interactive approval context를 사용해 프론트 허용/거절에 연결합니다. AX 캡처의 전체 텍스트를 제한 길이로 보존하는 로컬 패치는 provider-provenance.json에 기록합니다.

서버 재시작 전 기존 worker 상태만 확인하며 작업·중지 처리·모델 로딩·MCP 설치 중에는 재시작을 차단합니다. 준비 승인 시 새 요청을 차단한 뒤 상태를 재확인하고 IPC 쓰기와 직렬화해 시작/재시작 경합을 막습니다. 상태 확인 실패도 재시작 허용으로 처리하지 않습니다.

실행 안내는 문서 결과를 로컬 Markdown 링크로 보고하도록 설명합니다. 플랫폼 HTML 미리보기는 정적 HTML·인라인 CSS를 지원하고 스크립트·외부 자원은 차단하므로, 단순 문서 열람을 위해 별도 메모장·브라우저를 실행하지 않도록 안내합니다. 이는 모델에 전달하는 지침이며 모든 모델이 이를 따랐다는 실행 검증은 아닙니다.

실행 정책: 프로젝트 지침 자동 주입·출력 한도·reasoning은 원본 AIAgent 기본값을 사용합니다. 일반 작업의 기억·스킬 검토도 원본 조건과 auxiliary.background_review 설정에 맡깁니다. 읽기 전용 작업만 검토 쓰기를 막습니다. execution.py는 모델별 문맥 설정 연결과 검토 종료 대기를 담당하며, 검토 중에는 worker 작업 소유권을 유지해 모델 내리기·서버 재시작이 겹치지 않게 합니다.

2026-10-16: 격리된 가짜 모델 서버를 통해 원본 지침 주입, 강제 출력 제한·reasoning 비활성화 제거, 원본 스킬 검토 종료, 읽기 전용 도구 차단을 확인했습니다. 실제 Ornith의 thinking 출력·문맥 할당·품질 비교는 실행하지 않았습니다. 설치된 llama.cpp 도움말에서도 ctx-size 0이 모델 문맥을 사용하는 값임을 확인했습니다.
