# AI Agent

AI Agent compatibility namespace. Actual program ownership and automatic registration now live under modules/. Finance and REA do not own this project.

- [Hermes](../../modules/hermes/README.md): transplanted engine, chat, models, sessions, MCP and skills.

Call flow: feature → Hermes manager → module manifest → platform registry → existing single `/api`. `platform_modules.mount_namespaces()` preserves the `ai_agent.Hermes` Python imports without a fixed Hermes path in the coordinator.
