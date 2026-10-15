# Conversation workspace

Chat.tsx owns sessions, search, per-session drafts, send/stop/approval/resume, panel controls and scroll following. ChatStream.tsx groups adjacent tool-only turns and matches results by ID; ActivityTimeline pairs real start/complete events and retains errors. MessageBody.tsx renders Markdown/GFM with raw HTML disabled and provides copy controls.

The message area fills the remaining viewport. Latest Message restores scroll following. Selected active sessions refresh every 2.5 seconds, retaining unchanged message arrays to avoid reparsing Markdown for metrics-only updates. Opening settings keeps chat mounted. Drafts survive settings navigation and page reload.

The conversation and composer share a centered 880px reading width on large screens. User bubbles align with that column rather than the monitor edge; the surrounding workspace and header still fill the available viewport. Smaller screens use the available width.

The rounded composer starts as a single row with the run mode and send/stop control beside the text. Multiline input grows vertically and goal/loop options wrap below when selected. Decorative assistant marks are hidden; tool records align with the answer text.

Mobile sessions/activity use dismissible overlays with Escape, keyboard focus containment and focus restoration. The composer grows to 160px and then scrolls internally. No polling or navigation launches a model or task.

Context, generation speed, input/output tokens, request count and elapsed time are always visible in the existing conversation header beside the model name. No popup or activity panel is required; missing engine values remain —.

ChatHeader, SessionSidebar, ActivityPanel, ChatComposer and ChatWelcome are controlled presentation components. Button/IconButton and Input/Select/Textarea come from the shared UI primitives. The composer reads its resize bounds from the common Tailwind stylesheet rather than duplicating design constants in JavaScript.
