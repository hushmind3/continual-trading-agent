# Chat and autonomous execution

HTTP start/status/stop adapters call the original AIAgent in the isolated worker. Chat runs once. Goal and recurring modes use the original hermes_cli.goals.GoalManager and hermes_cli.loops.LoopManager; autonomy.py only drives these managers and forwards progress. The original auxiliary goal judge uses the selected model endpoint.

프로젝트 설치기의 자동 변환 요청은 chat의 workspace 값으로 해당 내려받은 프로젝트를 작업 폴더로 지정합니다. 이 값은 해당 실행의 cfg에만 적용하고 저장된 기본 작업 환경을 바꾸지 않습니다. 모델 준비·도구 승인·중지 경로는 기존 대화 실행과 같습니다.

원본 앱의 하네스 호출은 `application_system_prompt`로 역할과 응답 규격을 전달합니다(문자열 50,000자 이하). `engine/worker.py`가 실행별 ephemeral 시스템 지침에 추가하며 저장된 사용자 시스템 프롬프트는 변경하지 않습니다. 과거 앱 대화는 참고 자료로 구분하고 현재 요청만 수행합니다. 기존 모델·thinking·도구 권한·소유자 승인 경로를 그대로 사용합니다.

`application_response_format=json_object`는 OpenAI 호환 chat_completions 전송에만 JSON 제약을 요청합니다. runtime_policy.py가 기존 request_overrides와 병합하므로 thinking 옵션을 지우지 않습니다. 다른 전송의 JSON 계약은 앱 반환 시 검증하며 지원하지 않는 형식을 임의 변환하지 않습니다.

`application_plan_only=true`인 Project Zero 계획 요청은 JSON 문법과 도구 문법의 Ollama 충돌을 피하도록 해당 요청의 도구 전송만 비웁니다. 실제 `agent_task` 실행은 이 플래그 없이 일반 도구 경로를 사용합니다. 저장된 사용자 도구 목록/권한은 변경하지 않습니다.

`application_generation`은 원본 앱의 출력 한도(max_tokens 1~65,536 정수)와 temperature(0~2 숫자)를 실행별로 전달합니다. 원본 provider의 인수를 보존하기 위한 경로이며 전역 기본 제한이 아닙니다. runtime_policy에서 검증하고 원본 agent의 해당 실행에만 적용합니다.

Frontend modes: one turn, work toward a goal, recurring task. /goal <task>, /goal resume, /loop <interval> <task>, /loop resume and /stop also use the same paths. Tool approval and user-question callbacks remain interactive.

Goals stop when judged done, blocked, interrupted or budget-limited. Loops stop on the native completion marker, requested count, until criterion or native backstop. Intervals are clamped to the original minimum (30 seconds by default); self-paced mode starts at 60 seconds and backs off on unchanged responses. A model can signal completion before the requested count. Zero count uses the native 100-tick backstop, rather than implying unlimited work.

State lives in the native session DB. Stop pauses autonomous work. After a worker restart, opening a formerly active session marks it paused and offers Resume; it does not silently restart work. The platform backend must stay running for recurring execution. This is in-session /loop, not an OS scheduler or the standalone Hermes cron gateway. Status polling alone never starts a model or task.

telemetry.py reads original agent usage counters and the owned local llama.cpp /slots endpoint, cached for at least 0.8 seconds. Generation speed is sampled from actual decoded-token deltas while the same task is processing; missing observations stay unknown. Status retains final counters after agent cleanup. Tool events delimit the current streamed response and phase.

The worker tells the original agent its Windows host and detected browser executable, explains that Git Bash ps/which cannot identify Windows applications reliably, and directs visible GUI launches through detached PowerShell Start-Process. It must verify once, leave the requested app open, and not relaunch after the user closes it. This is operating-context guidance, not a replacement for native tools or proof that every model obeys it.

For visible Chrome/Edge launch, desktop_browser.py adds a platform extension through the original registry and explicit computer_use toolset membership. It resolves known installed browser executables, validates http/https/about:blank, starts the executable with a shell-free detached argument list, and suppresses duplicate same-turn launches. It reports only a launch request; native computer_use accessibility capture verifies the visible window. The existing AIAgent and native desktop/browser tools remain in use. This helper is platform code, not claimed to be part of the original Hermes source.

A native failed/incomplete/budget-exhausted result becomes paused with an explicit incomplete message rather than complete. Tool-loop errors remain visible in grouped results.

읽기 전용 분석은 설정의 read_only 권한으로 켭니다. 선택 작업 폴더 안의 read_file·search_files만 실행 전 허용하며 편집·명령·코드 실행·위임·MCP·컴퓨터 도구는 차단합니다. 원본 AIAgent는 유지하고 로컬 배치 실행 경계에 권한 검사를 둡니다. 대화 DB·로그 저장은 계속하며, 이 기능은 전체 프로세스를 OS 샌드박스에 넣는 기능은 아닙니다. 각 자동 실행 턴의 failed/completed 상태를 목표 판정 전에 확인하고 미완료 시 일시정지합니다.
