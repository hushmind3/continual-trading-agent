# Hermes

One submenu with Chat, Model settings, MCP and Skills tabs. Session selection/history/archive are part of Chat. Feature components live in matching folders. The backend reuses original AIAgent, SessionDB, MCP and skill functions; the React components provide this platform's interface only.

All requests target `ai_agent/Hermes/*` through the existing `/api` transport. Sending is asynchronous; polling retrieves streaming text and tool progress. Unmount cancels polling, not the user's task. No model/tool execution occurs on page load.
