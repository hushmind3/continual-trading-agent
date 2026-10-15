# Chat

Chat.tsx owns sessions, draft, send/stop/approval/resume, foldable session rail and optional activity pane. ChatStream.tsx groups an assistant tool call with its matching tool result and shows actual runtime counters. Empty assistant/tool-only messages do not produce repeated chat bubbles.

The message area fills the remaining viewport. Scroll follows new content only while the user is near the bottom. Sessions refresh every 2.5 seconds only during the selected active job. Settings leaves the chat mounted. Native output remains text, never executable HTML.
