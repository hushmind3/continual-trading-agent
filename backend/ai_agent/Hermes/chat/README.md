# Chat and autonomous execution

HTTP start/status/stop adapters call the original AIAgent in the isolated worker. Chat runs once. Goal and recurring modes use the original hermes_cli.goals.GoalManager and hermes_cli.loops.LoopManager; autonomy.py only drives these managers and forwards progress. The original auxiliary goal judge uses the selected model endpoint.

Frontend modes: one turn, work toward a goal, recurring task. /goal <task>, /goal resume, /loop <interval> <task>, /loop resume and /stop also use the same paths. Tool approval and user-question callbacks remain interactive.

Goals stop when judged done, blocked, interrupted or budget-limited. Loops stop on the native completion marker, requested count, until criterion or native backstop. Intervals are clamped to the original minimum (30 seconds by default); self-paced mode starts at 60 seconds and backs off on unchanged responses. A model can signal completion before the requested count. Zero count uses the native 100-tick backstop, rather than implying unlimited work.

State lives in the native session DB. Stop pauses autonomous work. After a worker restart, opening a formerly active session marks it paused and offers Resume; it does not silently restart work. The platform backend must stay running for recurring execution. This is in-session /loop, not an OS scheduler or the standalone Hermes cron gateway. Status polling alone never starts a model or task.

telemetry.py reads original agent usage counters and the owned local llama.cpp /slots endpoint, cached for at least 0.8 seconds. Generation speed is sampled from actual decoded-token deltas while the same task is processing; missing observations stay unknown. Status retains final counters after agent cleanup. Tool events delimit the current streamed response and phase.

The worker tells the original agent its Windows host and detected browser executable, explains that Git Bash ps/which cannot identify Windows applications reliably, and directs visible GUI launches through detached PowerShell Start-Process. It must verify once, leave the requested app open, and not relaunch after the user closes it. This is operating-context guidance, not a replacement for native tools or proof that every model obeys it.

For visible Chrome/Edge launch, desktop_browser.py adds a platform extension through the original registry and explicit computer_use toolset membership. It resolves known installed browser executables, validates http/https/about:blank, starts the executable with a shell-free detached argument list, and suppresses duplicate same-turn launches. It reports only a launch request; native computer_use accessibility capture verifies the visible window. The existing AIAgent and native desktop/browser tools remain in use. This helper is platform code, not claimed to be part of the original Hermes source.

A native failed/incomplete/budget-exhausted result becomes paused with an explicit incomplete message rather than complete. Tool-loop errors remain visible in grouped results.

읽기 전용 분석은 설정의 read_only 권한으로 켭니다. 선택 작업 폴더 안의 read_file·search_files만 실행 전 허용하며 편집·명령·코드 실행·위임·MCP·컴퓨터 도구는 차단합니다. 원본 AIAgent는 유지하고 로컬 배치 실행 경계에 권한 검사를 둡니다. 대화 DB·로그 저장은 계속하며, 이 기능은 전체 프로세스를 OS 샌드박스에 넣는 기능은 아닙니다. 각 자동 실행 턴의 failed/completed 상태를 목표 판정 전에 확인하고 미완료 시 일시정지합니다.
