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

- A real model endpoint/model has not been selected or called. Real autonomous model quality and real-model coding tasks are unverified.
- Local GGUF load/unload is connected to the installed llama-server with GPU layers requested; actual weight loading and GPU inference were not run in this work.
- Desktop click/type and agent-driven browser tasks were not run. Remote/authenticated MCP servers were not available for testing.
- Optional upstream skills can require their own software or credentials. Listing/reading a skill does not mean every external integration is installed or authenticated.

## Use

1. Open AI Agent → Hermes → Model settings. Connect an OpenAI-compatible endpoint and select a model, or explicitly load a local GGUF listed from the model folder. Save the workspace and tool selection.
2. Configure MCP servers if needed, save, then connect to discover tools.
3. Start a chat/session, send a task and watch progress. Answer native questions/confirmations when shown; Stop interrupts the active task.

The separate original source directory may be removed by the user; the transplant and setup use the copies and dependencies inside this project. Original deletion was not performed.
