# AI Agent

Independent large menu. `submenu_manager.py` collects Hermes; `ai_agent_menu_manager.py` registers it with the platform menu registry. Finance and REA do not own this project.

- [Hermes](Hermes/README.md): transplanted engine, chat, models, sessions, MCP and skills.

Call flow: feature → Hermes manager → AI Agent manager → platform registry → existing single `/api`.
