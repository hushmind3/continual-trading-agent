# Conversation workspace

Chat.tsx owns sessions, search, per-session drafts, send/stop/approval/resume, panel controls and scroll following. ChatStream.tsx groups adjacent tool-only turns and matches results by ID; ActivityTimeline pairs real start/complete events and retains errors. MessageBody.tsx renders Markdown/GFM with raw HTML disabled and provides copy controls.

The message area fills the remaining viewport. Latest Message restores scroll following. Selected active sessions refresh every 2.5 seconds, retaining unchanged message arrays to avoid reparsing Markdown for metrics-only updates. Opening settings keeps chat mounted. Drafts survive settings navigation and page reload.

The conversation and composer share a centered 880px reading width on large screens. User bubbles align with that column rather than the monitor edge; the surrounding workspace and header still fill the available viewport. Smaller screens use the available width.

The rounded composer starts as a single row with the run mode and send/stop control beside the text. Multiline input grows vertically and goal/loop options wrap below when selected. Decorative assistant marks are hidden; tool records align with the answer text.

Mobile sessions/activity use dismissible overlays with Escape, keyboard focus containment and focus restoration. The composer grows to 160px and then scrolls internally. No polling or navigation launches a model or task.

Context, generation speed, input/output tokens, request count and elapsed time are always visible in the existing conversation header beside the model name. No popup or activity panel is required; missing engine values remain —.

ChatHeader, SessionSidebar, ActivityPanel, ChatComposer and ChatWelcome are controlled presentation components. Button/IconButton and Input/Select/Textarea come from the shared UI primitives. The composer reads its resize bounds from the common Tailwind stylesheet rather than duplicating design constants in JavaScript.

동일한 문장을 다시 보내도 현재 전송 이후에 저장된 메시지만 대조합니다. 전송으로 새 세션이 생기면 sessionStorage에 즉시 기록합니다. 로컬 문서 링크·인라인 문서 경로는 공통 DocumentPreview로 열며 성공한 write_file/patch 결과 파일은 접힌 도구 기록 바깥에도 표시합니다. Markdown·텍스트 미리보기만 지원하며 파일 실행·HTML 실행은 하지 않습니다.

대화 본문에는 사용자·에이전트 메시지와 결과 파일만 표시합니다. 도구 요청·결과·오류와 현재 실행 명령은 오른쪽 작업 내역에 모읍니다. 현재 이벤트가 없는 과거 세션은 저장된 도구 호출·결과를 작업 내역에서 확인합니다.

작업 내역의 과거 기록도 단계별 단일 목록입니다. 명령·파일 경로를 접힌 상태에서 바로 보여주며 작업 기록 안에 작업 기록을 중첩하지 않습니다. 도구 호출을 포함한 assistant 진행 설명은 대화 본문에 반복 표시하지 않습니다.

결과 문서는 데스크톱에서 대화 옆의 독립 패널로 열립니다. 대화 입력을 막지 않으며 문서·소스 전환과 Escape 닫기를 제공합니다. 모바일에서는 전체 폭 패널로 표시합니다. 작업 내역과 문서 패널은 같은 오른쪽 공간을 사용합니다.

파일 첨부 버튼·클립보드 파일 붙여넣기를 지원합니다. 파일당 8 MiB·요청당 8개이며 runtime/ai_agent/Hermes/artifacts/uploads에 저장한 경로를 메시지와 함께 전달합니다. 파일 등록은 모델의 이미지 이해를 뜻하지 않습니다. 실행 중에도 다음 요청의 모드·횟수·첨부는 준비할 수 있고, 현재 실행은 중지 버튼으로 제어합니다.
