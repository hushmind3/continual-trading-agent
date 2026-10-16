# Settings

Settings.tsx owns model/MCP/skills navigation: a descriptive sidebar on desktop and compact tabs on mobile. The last section persists for the browser session; the model chip explicitly opens Models. Child modules live in models/, mcp/ and skills/. Chat remains mounted behind settings, preserving draft and session. Navigation does not start a model or tool.

prompt/SystemPrompt.tsx: 시스템 프롬프트를 설정 API에 저장합니다. 원본 AIAgent의 추가 시스템 지침 인자로 연결하며 새 대화·기존 대화의 다음 요청부터 적용합니다.
