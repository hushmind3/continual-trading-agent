# Conversation workspace

Chat.tsx owns sessions, search, per-session drafts, send/stop/approval/resume, panel controls and scroll following. ChatStream.tsx groups adjacent tool-only turns and matches results by ID; ActivityTimeline pairs real start/complete events and retains errors. MessageBody.tsx renders Markdown/GFM with raw HTML disabled and provides copy controls.

The message area fills the remaining viewport. Latest Message restores scroll following. Selected active sessions refresh every 2.5 seconds, retaining unchanged message arrays to avoid reparsing Markdown for metrics-only updates. Opening settings keeps chat mounted. Drafts survive settings navigation and page reload.

Mobile sessions/activity use dismissible overlays with Escape, keyboard focus containment and focus restoration. The composer grows to 160px and then scrolls internally. No polling or navigation launches a model or task.
