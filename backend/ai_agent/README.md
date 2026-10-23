# AI Agent

AI Agent compatibility namespace. Actual program ownership and automatic registration now live under modules/. Finance and REA do not own this project.

- [Hermes](../../modules/hermes/README.md): transplanted engine, chat, models, sessions, MCP and skills.

Call flow: feature → Hermes manager → module manifest → platform registry → existing single `/api`. `platform_modules.mount_namespaces()` preserves the `ai_agent.Hermes` Python imports without a fixed Hermes path in the coordinator.

- [헤르메스 원본](../../modules/hermes_original/README.md): 전체 공식 체크아웃·공식 PM·원본 dashboard/CLI. 기존 이식본과 별도 홈을 사용합니다.
- [OpenClaw 원본](../../modules/openclaw_original/README.md): 공식 OpenClaw 저장소와 독립 Node 실행 환경. 원본 Control UI를 기존 단일 `/api` lifecycle에 연결합니다.
