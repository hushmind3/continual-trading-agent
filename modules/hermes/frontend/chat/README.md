# Conversation workspace

용도: Hermes 대화 소메뉴의 화면 구성·설정 전달·검사 인수인계입니다.

Chat.tsx owns sessions, search, per-session drafts, send/stop/approval/resume, panel controls and scroll following. ChatStream.tsx groups adjacent tool-only turns and matches results by ID; ActivityTimeline pairs real start/complete events and retains errors. MessageBody.tsx renders Markdown/GFM with raw HTML disabled and provides copy controls.

The message area fills the remaining viewport. Latest Message restores scroll following. Selected active sessions refresh every 2.5 seconds, retaining unchanged message arrays to avoid reparsing Markdown for metrics-only updates. Opening settings keeps chat mounted. Drafts survive settings navigation and page reload.

The conversation and composer share a centered 880px reading width on large screens. User bubbles align with that column rather than the monitor edge; the surrounding workspace and header still fill the available viewport. Smaller screens use the available width.

The composer uses a full-width writing row and a separate toolbar at all viewport widths. Multiline input grows vertically and goal/loop options wrap below when selected. ComposerFrame and FileChips are shared UI components; RunModeOptions owns the mode fields. Decorative assistant marks are hidden; tool records align with the answer text.

Mobile sessions/activity use dismissible overlays with Escape, keyboard focus containment and focus restoration. The composer grows to 160px and then scrolls internally. No polling or navigation launches a model or task.

Context, generation speed, input/output tokens, request count and elapsed time are always visible in the existing conversation header beside the model name. No popup or activity panel is required; missing engine values remain —.

ChatHeader, SessionSidebar, ActivityPanel, ChatComposer and ChatWelcome are controlled presentation components. Button/IconButton and Input/Select/Textarea come from the shared UI primitives. The composer reads its resize bounds from the common Tailwind stylesheet rather than duplicating design constants in JavaScript.

동일한 문장을 다시 보내도 현재 전송 이후에 저장된 메시지만 대조합니다. 전송으로 새 세션이 생기면 sessionStorage에 즉시 기록합니다. 로컬 문서 링크·인라인 문서 경로는 공통 DocumentPreview로 열며 성공한 write_file/patch 결과 파일은 접힌 도구 기록 바깥에도 표시합니다. Markdown·텍스트와 샌드박스 HTML 미리보기를 지원합니다. HTML 스크립트·외부 리소스 요청·폼 전송은 차단합니다.

대화 본문에는 사용자·에이전트 메시지와 결과 파일만 표시합니다. 도구 요청·결과·오류와 현재 실행 명령은 오른쪽 작업 내역에 모읍니다. 현재 이벤트가 없는 과거 세션은 저장된 도구 호출·결과를 작업 내역에서 확인합니다.

작업 내역의 과거 기록도 단계별 단일 목록입니다. 명령·파일 경로를 접힌 상태에서 바로 보여주며 작업 기록 안에 작업 기록을 중첩하지 않습니다. 도구 호출을 포함한 assistant 진행 설명은 대화 본문에 반복 표시하지 않습니다.

결과 문서는 데스크톱에서 대화 옆의 독립 패널로 열립니다. 대화 입력을 막지 않으며 문서·소스 전환과 Escape 닫기를 제공합니다. 모바일에서는 전체 폭 패널로 표시합니다. 작업 내역과 문서 패널은 같은 오른쪽 공간을 사용합니다.

파일 첨부 버튼·클립보드 파일 붙여넣기를 지원합니다. 파일당 8 MiB·요청당 8개이며 runtime/ai_agent/Hermes/artifacts/uploads에 저장한 경로를 메시지와 함께 전달합니다. 파일 등록은 모델의 이미지 이해를 뜻하지 않습니다. 실행 중에도 다음 요청의 모드·횟수·첨부는 준비할 수 있고, 현재 실행은 중지 버튼으로 제어합니다.

문서를 연 상태에서는 대화·입력창이 같은 왼쪽 열에 남고 문서가 오른쪽 높이를 모두 사용합니다. 화면 폭이 좁으면 실행 수치는 가로로 읽는 한 줄이며, 엔진 압축 요약·출력 한도 메모는 EngineNotes를 통해 작업 내역에서만 펼칩니다(원본 기록은 유지).

대화 기록은 임시 선택 패널입니다. 대화 선택 후 닫히고, 열 때 작업 내역·문서와 동시에 본문 공간을 나누지 않습니다. 데스크톱에서도 Escape·키보드 초점 순환을 지원합니다. 대화 보관은 기록 패널에 두며 작업 중인 대화는 보관할 수 없습니다. 본문 문서 링크는 공통 텍스트 링크 스타일로 표시합니다.

대화 기록의 이름 바꾸기는 해당 행에서 입력·저장·취소합니다. session/rename API가 성공하면 목록과 헤더 제목만 갱신하며 선택 대화·기록·초안은 유지합니다.

실행 수치는 RuntimeMetrics.tsx, 실행 버튼은 HeaderActions.tsx로 분리했습니다. 모델 옆에 여섯 항목을 같은 크기의 작은 라벨·값으로 정렬하고 미수신 값은 —로 표시합니다. 모델명 옆의 실행 중·불러오는 중·미실행·연결 오류는 백엔드가 보고한 모델 상태입니다. 대화·작업 패널은 기본 닫힘이며 자료가 없는 수치를 임의 계산하지 않습니다.

읽기 모드는 입력창의 스위치로 켜고 끕니다. 전송·재개 요청의 read_only 값이 해당 작업에 적용되며, 기존 작업 환경의 권한 기본값보다 우선합니다. 작업 중에도 다음 요청의 스위치는 바꿀 수 있습니다. 선택은 브라우저에 기억하고 시스템 프롬프트 저장과 분리합니다.

데스크톱 작업 내역·문서는 왼쪽 경계를 드래그해 폭을 조절합니다. 방향키 조절·더블클릭 기본 폭 복원·각 패널의 폭 기억을 지원합니다. 모바일에서는 전체 폭으로 표시하며 크기 조절 손잡이를 숨깁니다.

ThinkingControl.tsx·useThinking.ts는 읽기 모드 옆에서 Thinking 자동/켜기/끄기를 선택합니다. 로컬 모델에만 표시하고 모델별 선택을 브라우저에 기억합니다. 전송·재개 직전에 기존 /api/ai_agent/Hermes/settings에 thinking_mode를 저장한 뒤 chat을 호출합니다. 실행 중 선택은 다음 요청에 적용하며 진행 중 작업과 모델 적재 상태는 변경하지 않습니다. 원본 request_overrides 연결은 [백엔드 모델 안내](../../backend/models/README.md)를 따릅니다.

2026-10-18 확인: TypeScript·Vite 빌드, 모의 API 브라우저 검사 29개 통과. Thinking 선택 후 전송·작업 중 다음 값 변경·새로고침 복원·390px 가로 넘침 없음을 검사했습니다. 실제 1440px 화면에서 읽기 모드 옆 Thinking 끄기와 JavaScript 오류 0건을 확인했고 390px도 표시·넘침 없음을 확인했습니다. 이번 UI 이동은 백엔드·모델 재시작 없이 프론트만 적용했으며 실제 추론 비교 검사는 추가 실행하지 않았습니다.
