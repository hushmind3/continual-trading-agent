# Hermes transplant — 2026-10-16

## Implemented and applied

- Backend: independent `ai_agent/Hermes/` submenu under the AI Agent manager; registered through the existing platform registry and single `/api`. Finance code and the API transport were not changed.
- Frontend: `#ai_agent/Hermes`, with Chat, Model settings, MCP and Skills. Chat includes sessions, history, archive, tool progress, stop and native tool-confirmation/question responses.
- Execution: copied original AIAgent loop, SessionDB, file/terminal/browser/computer-use tool code, MCP and skills. This is not a rewritten agent loop and does not launch the original Hermes frontend, messaging gateway or standalone CLI.
- Source: local snapshot of upstream commit `09fa65c1470de425a92023d809076967be3c2727`. Original MIT license and source fingerprints are retained in `engine/`. Standalone entrypoints and unselected copied code were moved into the project trash. Shared CLI/config/approval helpers remain where required. The original checkout has not been modified or deleted.
- Runtime: reuse installed Python 3.14.7 through `.venv/hermes/`; 73 installed packages pass `uv pip check`. Finance Python stays unchanged. The native desktop driver is the source-pinned cua-driver 0.21.0, archive SHA-256 verified by setup. All configuration, sessions and tool state resolve inside this project; there is no original-checkout PYTHONPATH, editable dependency or symlink.
- Runtime bootstrap no longer activates the upstream package manager or re-launches the source installer. Lazy package installation is disabled. Setup is explicit and pinned in `engine/requirements.lock.txt`.

## Actually verified

- Copied engine import and execution in an isolated Python process. Loaded Hermes engine modules resolve to the transplanted source directory.
- Controlled OpenAI-compatible model-protocol fixture drives the original loop to execute `write_file`; the file contents are checked in the selected workspace. This uses a test response server, not a real LLM.
- Native session history retains user/assistant/tool messages, survives worker restart and supports another turn. Session archive hides the session without deleting its history.
- Native stop, settings validation and model discovery.
- Native MCP SDK connects to a local stdio fixture, discovers its tool and executes it through the engine's own tool_search → tool_describe → tool_call path.
- 51 native bundled skills are listed and original skill contents are readable.
- Native cua-driver contract passes; original desktop backend starts and reads the real running-app list (227 entries in that check). No clicks, typing or application changes were performed.
- Frontend TypeScript check and Vite production build pass. Actual served React page opens all four tabs, reads skills and creates/archives a session. Desktop and 390px mobile views have no horizontal overflow; browser page errors: none. Screenshots are local runtime artifacts under `verification/`.
- Updated frontend and backend are served on port 8766. The launcher skipped the unrelated full-platform inspection; the targeted checks above were run separately.

## Not verified / remaining user configuration

- Broader autonomous coding quality across models is unverified. The tested 0.8B model initially invented a different output path; the adapter now supplies the exact workspace and an explicit-path task succeeded. Treat its plans and outputs as model-dependent.
- Other GGUF sizes and architectures were not loaded. Local inference was verified with Qwen3.5-0.8B and the user-selected Ornith-1.5-9B.Q4_K_M.
- Actual Ornith desktop click/type/confirmation-read and browser navigate/type/click/snapshot now pass in controlled local fixtures (details below). Remote/authenticated MCP servers still require their own credentials and were not tested.
- Optional upstream skills can require their own software or credentials. Listing/reading a skill does not mean every external integration is installed or authenticated.

## Use

1. Open AI Agent → Hermes → Model settings. Connect an OpenAI-compatible endpoint and select a model, or explicitly load a local GGUF listed from the model folder. Save the workspace and tool selection.
2. Configure MCP servers if needed, save, then connect to discover tools.
3. Start a chat/session, send a task and watch progress. Answer native questions/confirmations when shown; Stop interrupts the active task.

The separate original source directory may be removed by the user; the transplant and setup use the copies and dependencies inside this project. Original deletion was not performed.

## Local usability corrections — 2026-10-16

- Korean menu, tabs, tool labels and skill titles; redesigned desktop/mobile layout; local model list and load-to-chat flow; form-based MCP setup with advanced JSON folded away. Native MCP schema and skill instructions remain unchanged.
- Real inference exposed a genuine blocker: Hermes rejects the previous 8K context. The owned llama-server now serves 65,536 tokens, one slot, two CPU helper threads, with GPU layers requested. Actual logs show recurrent layers and compute buffers on Vulkan0 / RTX 3070.
- The original AIAgent called write_file against the requested verification workspace and the resulting verified.txt contains HERMES_LOCAL_OK (with a trailing newline). It then replied in Korean. No original model file was rewritten, trained or quantized.
- Native unique-title generation fixes repeated new conversations; a regression assertion covers it. Five targeted engine/session/MCP/stop checks passed.
- Idle frontend recurring status polling was removed. Polls run while a task/model load is active and on focus/visibility resume.
- CPU sampling identified a project CCE indexer using about one full core, separate from the Hermes worker. Stopped both project-scoped CCE process trees after observing another existing tree continue indexing. Added .cceignore exclusions for vendored source, runtime, environments, build outputs and trash; matched exclusions were checked with the installed parser. Other applications were left running. This does not disable every external indexer or change global MCP configuration.
- Real-model verification artifacts and temporary sessions are runtime data, excluded from Git. The unintended first verification output was moved to project trash after checking its exact contents.

## User-selected Ornith verification

- Used the already-installed project llama.cpp server; no new engine or model download. Model: Desktop/모델/Ornith-1.5-9B.Q4_K_M.gguf (5,629,109,280 bytes). Native GGUF metadata identifies qwen35 with a 262,144-token training context.
- Served 65,536 tokens, one slot, GPU layers requested, two CPU helper threads, flash attention and Q8 KV caches. Model weights remain the existing Q4_K_M file. Root-level model files keep their filename as the model alias.
- Actual original AIAgent invoked write_file, created verification/local-task/ornith.txt containing exactly ORNITH_HERMES_OK, then replied in Korean. Final status: complete, no engine error. Result saved locally as verification/ornith-result.json.
- Restored the project workspace, original terminal/file/todo/skills selection and iteration limit after testing. Ornith remains loaded and ready at completion. Test sessions were archived without removing history.
- Current TypeScript check passed and production assets/backend were applied. Prior five targeted checks passed; no financial training, orders or source-model conversion ran.

## Desktop, browser and MCP completion — 2026-10-16

- Restored the original bundled cua provider registration (plugins/computer_use/cua/__init__.py and plugin.yaml), which had been omitted from the dynamic dependency closure. Fingerprints: engine/provider-provenance.json.
- Bound the native interactive approval context to the chat thread and retained its callback to the platform approval UI; no approval bypass was enabled. A task stays running until cleanup finishes, fixing the completed-but-still-busy race.
- Added original-lock-pinned agent-browser 0.26.0 as a backend npm workspace with shared root node_modules. Uses installed Chrome/Edge. Selected the native agent-browser stack explicitly rather than the default browser-use CLI. Selected core tool schemas are visible directly; native MCP discovery remains available.
- Preserved up to 8,000 characters of the original AX capture text alongside unchanged element indices. The original element-only payload dropped input values/static result text. This deliberate local adaptation is recorded with original/adapted hashes.
- Actual Ornith-1.5-9B.Q4_K_M, original AIAgent and original computer_use: captured a real Windows Forms test app, clicked its input, typed DESKTOP_HERMES_OK, clicked Confirm, and read Confirmed: DESKTOP_HERMES_OK from a subsequent native capture. The application-written result file and actual tool history were both asserted. Test passed (29.964 seconds).
- Actual same Ornith and original browser tools: navigated a local page in Chromium, filled BROWSER_HERMES_OK, clicked Confirm and read the rendered confirmation in browser_snapshot. Local page POST and four distinct tool calls were asserted. Test passed as part of the 49.132-second live run.
- Five existing targeted engine/session/MCP/stop checks pass. Live GUI checks are opt-in with HERMES_LIVE_TOOLS=1 and use temporary project runtime state; ordinary test discovery does not launch models or windows.
- MCP UI now shows built-in capabilities, connection/tool counts, local/remote setup choices, JSON config import, search, edit, errors and removal. Browser verification imported an actual MCP config, connected a local stdio server, observed one tool, edited without losing its env field, removed the connection and restored the previous configuration. Desktop/mobile layout checks passed without horizontal overflow.
- No claim is made that every third-party app/site is compatible. Text-only GGUF operation uses accessibility trees; canvas-only screens require a suitable vision model/projector. No user authentication, external messages, financial orders, model training or quantization were performed.

## Native catalog, skills and autonomous modes — 2026-10-16

- Restored all 65 original optional-mcps manifests, fingerprinted in engine/provider-provenance.json. The original catalog card installer and validated native MCP configuration writer are exposed through the existing platform API; no standalone Hermes gateway is needed. Remote installation registers the endpoint, while Git-based entries use their original bootstrap instructions. Catalog registration is distinct from authenticated connection.
- Frontend External Tools now has Install Catalog and My Connections: Korean descriptions, original setup/auth notes, official source links, required settings dialog, install progress and enable/disable. Real browser verification installed alltrails into native configuration, toggled it off/on and restored the previous empty server map. No remote AllTrails connection or OAuth login was attempted. This is the curated original catalog, not an internet search engine.
- All 51 original skills have individual Korean summaries, original descriptions/instructions, search/category/activation filters, essential-skill protection, activation switches and create/edit forms. Native guarded writers handle saving. Isolated integration checks created/edited a skill and verified activation survives worker reopening. Browser checks read arxiv instructions, toggled it off/on, and opened both editors.
- Chat exposes one turn, goal and recurring modes. Original GoalManager/LoopManager own judgments, completion markers, waits, budgets, persistence and cadence; the platform driver calls the original AIAgent again when these managers request it. Native /goal, /loop, pause and resume commands share these paths. Stop retains state for resumption; disconnected persisted sessions are marked paused when opened. OS cron scheduling is not part of this change.
- Actual Ornith 9B goal execution created goal.txt containing GOAL_OK; the native goal judge returned done. An initial recurring instruction was ended by Ornith's native LOOP_COMPLETE marker after one tick; this was not reported as a two-tick success. With an explicit overall target of two scheduled increments, actual Ornith ran two separate wakeups 30 seconds apart and the counter file reached 2. No extra model weights or ORIGINAL.pt files were created. Local evidence: runtime/ai_agent/Hermes/verification/autonomy-live/goal-result.json and autonomy-final/loop-result.json.
- Seven targeted integration checks passed, covering original chat/tool history, native MCP discovery and invocation, interruption, catalog registration, skills persistence/editing and native loop stop/reopen/resume to the second tick. TypeScript and production build passed. Browser checks found 65 catalog cards and 51 skills, and mobile chat had no horizontal overflow or page errors. External OAuth login, every third-party MCP service, OS-level scheduling and behavior on arbitrary long goals remain unverified.

- Final applied-UI check: selected Goal mode, set the two-turn budget and sent the task from the frontend. Ornith invoked the original terminal tool, created frontend-goal.txt with FRONTEND_GOAL_OK and read it back. The native judge returned done, job state complete, with no engine error. The actual file contents were independently checked. Runtime evidence: verification/frontend-goal-result.json. The test conversation was archived; Ornith remains loaded and ready.

## Conversation workspace and runtime visibility — 2026-10-16

- Replaced the large title/intro/four-tab area with a compact Conversation/Settings toolbar. Only the Hermes route removes the surrounding page gutters and fills the available viewport. Settings now physically contains models/, mcp/ and skills/; engine routes remain unchanged. Chat stays mounted while settings are open, preserving its draft and session.
- Sessions are collapsed by default and can be opened as a sidebar or mobile drawer. A separate optional activity pane shows current job events; a compact current-action row remains visible during work. Assistant tool calls and their results share one disclosure row, avoiding repeated empty assistant bubbles and disconnected tool-result boxes. Scroll follows new output only near the bottom.
- Added native input/output/API counters, context usage/limit, elapsed seconds and sampled generation tokens/second. Token speed uses owned llama.cpp decoded-token deltas, not character estimates; no measurements render as unknown/waiting. Actual Ornith observations included context 12,713/65,536 and 59.7 tok/s. These are observed sample values, not benchmark guarantees.
- Browser checks verified session open/close, activity pane, draft persistence through settings, 65 MCP entries and 51 skills after physical moves. At 1440x1000 the message area was about 569px high and the page fit the viewport. At 390x844 the message area was about 437px, the composer remained visible, and there was no horizontal overflow.
- Investigated the user's actual Chrome history: Git Bash ps/which searches were inappropriate for native Windows apps, and the final command wrapped Chrome in timeout 10. A prompt-only correction still failed in actual Ornith due to shell/path quoting. These failed attempts were not classified as successful browser execution. Added the explicitly platform-owned desktop_browser extension: known installed browser paths, validated URLs, detached shell-free arguments, duplicate-launch suppression and no automatic window cleanup. Native tool discovery and explicit built-in GUI membership expose the helper directly to the model; original computer_use remains responsible for visual verification. Provenance marks this adapter as a platform addition.
- Native incomplete/budget-exhausted runs now show paused/incomplete with their reason, instead of complete. The failed four-iteration launch was observed in this state. Seven targeted integration checks passed after telemetry/UI changes; the additional model-visible browser-tool regression passed after correcting native discovery/deferral (eight targeted cases total). TypeScript and production build passed; current assets and backend were applied.

- Final actual Ornith launch passed after direct GUI tool exposure: desktop_browser(browser=chrome,url=about:blank) followed by original computer_use(action=capture,mode=ax), then a complete response with no error. Native capture included Chrome, the window was left open, and no close/relaunch command was issued. Elapsed 16.7 seconds; runtime evidence is verification/chat-layout/chrome-launch-verified.json. Earlier failed/pending attempts remain recorded separately and were not relabeled as success. The model's free-form answer quality remains model-dependent.
