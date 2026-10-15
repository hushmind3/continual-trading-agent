# Chat and autonomous execution

HTTP start/status/stop adapters call the original AIAgent in the isolated worker. Chat runs once. Goal and recurring modes use the original hermes_cli.goals.GoalManager and hermes_cli.loops.LoopManager; autonomy.py only drives these managers and forwards progress. The original auxiliary goal judge uses the selected model endpoint.

Frontend modes: one turn, work toward a goal, recurring task. /goal <task>, /goal resume, /loop <interval> <task>, /loop resume and /stop also use the same paths. Tool approval and user-question callbacks remain interactive.

Goals stop when judged done, blocked, interrupted or budget-limited. Loops stop on the native completion marker, requested count, until criterion or native backstop. Intervals are clamped to the original minimum (30 seconds by default); self-paced mode starts at 60 seconds and backs off on unchanged responses. A model can signal completion before the requested count. Zero count uses the native 100-tick backstop, rather than implying unlimited work.

State lives in the native session DB. Stop pauses autonomous work. After a worker restart, opening a formerly active session marks it paused and offers Resume; it does not silently restart work. The platform backend must stay running for recurring execution. This is in-session /loop, not an OS scheduler or the standalone Hermes cron gateway. Status polling alone never starts a model or task.
