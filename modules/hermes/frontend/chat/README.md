# Conversation workspace

용도: Hermes 대화 소메뉴의 화면 구성·설정 전달·검사 인수인계입니다.

2026-10-20 실제 기존 설치본 확인: 총괄 대상 선택·새로고침 유지·EstimateAI 기존 미리보기 HTTP 200 확인. 기존 총괄 세션의 회사 기록 조회는 GPT-6-Luna/low에서 13초·모델 3회로 완료됐습니다. 로컬 Ornith의 동일 누적 세션은 자동 압축 장기 대기로 완료 확인하지 못했습니다. 생성해 확인하던 검사 전용 HTML/스크립트는 휴지통으로 옮겼고, 설치본을 다시 받거나 새 조직/제품을 만들지 않았습니다. TypeScript·Vite 빌드는 통과했으며 로컬 모델은 ready로 복구했습니다. 이 확인은 전체 사업 실행·배포 완료를 뜻하지 않습니다.

대화 대상(일반/조직별 AI 총괄)은 실행 방식(한 번/목표/반복)과 별도 선택입니다. 대상은 현재 native session_id로 판단해 상단·입력창에 계속 표시하며 전송으로 일반 대화로 바꾸지 않습니다. 일반 대화 복귀 시 마지막 일반 세션과 개별 초안을 복원합니다. 대상 전환 중 전송을 막고 늦은 전환 응답을 무시합니다. 회사 상태·승인 기능과 동일 Hermes DB/실행 경로는 유지합니다. 사업 관리는 기본으로 닫고 상단의 기존 버튼 하나로 열고 닫습니다. 패널의 중복 제목·닫기 줄은 없애되 사업 초안 카드와 승인·수정 안내는 항상 표시합니다. 사업 진행은 승인된 진행 프로젝트 수와 실제 dist/index.html이 있는 실행 가능한 제품 수를 표시하며 고객 요청·결제 매출은 표시하지 않습니다. 승인·보류 및 대화를 통한 초안 수정 흐름은 유지합니다. 제품 링크는 사업 관리에서 확인합니다. 총괄·일반 대화에는 기존 제품을 상시 배너로 붙이지 않습니다. 각 작업이 생성·수정한 파일은 해당 작업의 결과 파일 링크에서 엽니다. 색상·글꼴·카드는 공통 tailwind.css의 brand/ink/copy와 Pretendard 테마를 사용합니다.

RuntimeMetrics의 ‘전체 작업’은 모든 모델 요청·검색·도구 실행·대기를 합한 시간이며 API 한 번의 응답 시간이 아닙니다. 컨텍스트 안내에는 이전 대화·지침·도구 결과가 포함됨을 표시합니다. 생성 속도 미측정은 기존처럼 빈 값이며 전체 시간으로 추정하지 않습니다. 공통 테마와 이름이 표시된 추론 선택을 재사용합니다.

Chat.tsx owns sessions, search, per-session drafts, send/steer/stop/approval/resume, panel controls and scroll following. ChatStream.tsx groups adjacent tool-only turns and matches results by ID; ActivityTimeline pairs real start/complete events and retains errors. MessageBody.tsx renders Markdown/GFM with raw HTML disabled and provides copy controls.

The message area fills the remaining viewport. Latest Message restores scroll following. Selected active sessions refresh every 2.5 seconds, retaining unchanged message arrays to avoid reparsing Markdown for metrics-only updates. Opening settings keeps chat mounted. Drafts survive settings navigation and page reload.

The conversation and composer share a centered 880px reading width on large screens. User bubbles align with that column rather than the monitor edge; the surrounding workspace and header still fill the available viewport. Smaller screens use the available width.

The composer uses a full-width writing row and a separate toolbar at all viewport widths. Multiline input grows vertically and goal/loop options wrap below when selected. ComposerFrame and FileChips are shared UI components; RunModeOptions owns the mode fields. Decorative assistant marks are hidden; tool records align with the answer text.

Mobile sessions/activity use dismissible overlays with Escape, keyboard focus containment and focus restoration. The composer grows to 160px and then scrolls internally. No polling or navigation launches a model or task.

Context, generation speed, input/output tokens, request count and elapsed time are always visible in the existing conversation header beside the model name. No popup or activity panel is required; missing engine values remain —.

ChatHeader, SessionSidebar, ActivityPanel, ChatComposer and ChatWelcome are controlled presentation components. Button/IconButton and Input/Select/Textarea come from the shared UI primitives. The composer reads its resize bounds from the common Tailwind stylesheet rather than duplicating design constants in JavaScript.

동일한 문장을 다시 보내도 현재 전송 이후에 저장된 메시지만 대조합니다. 전송으로 새 세션이 생기면 sessionStorage에 즉시 기록합니다. 로컬 문서 링크·인라인 문서 경로는 공통 DocumentPreview로 열며 성공한 write_file/patch 결과 파일은 접힌 도구 기록 바깥에도 표시합니다. Markdown·텍스트와 샌드박스 HTML 미리보기를 지원합니다. HTML 스크립트·외부 리소스 요청·폼 전송은 차단합니다.

대화 본문에는 사용자·에이전트 메시지와 결과 파일을 표시합니다. 도구 요청·결과·오류는 접힌 실행 과정과 오른쪽 작업 내역에서 확인합니다. 현재 이벤트가 없는 과거 세션은 저장된 도구 호출·결과를 작업 내역에서 확인합니다.

작업 내역의 과거 기록도 단계별 단일 목록입니다. 명령·파일 경로를 접힌 상태에서 바로 보여주며 작업 기록 안에 작업 기록을 중첩하지 않습니다. 도구 호출 전 assistant 진행 설명은 본문에 유지해 스트리밍 종료 후 사라지지 않도록 합니다.

결과 문서는 데스크톱에서 대화 옆의 독립 패널로 열립니다. 대화 입력을 막지 않으며 문서·소스 전환과 Escape 닫기를 제공합니다. 모바일에서는 전체 폭 패널로 표시합니다. 작업 내역과 문서 패널은 같은 오른쪽 공간을 사용합니다.

파일 첨부 버튼·클립보드 파일 붙여넣기를 지원합니다. 파일당 8 MiB·요청당 8개이며 runtime/ai_agent/Hermes/artifacts/uploads에 저장한 경로를 메시지와 함께 전달합니다. 파일 등록은 모델의 이미지 이해를 뜻하지 않습니다. 실행 중에도 메시지·첨부를 전달할 수 있습니다. 모드·횟수·모델 설정 변경은 다음 실행에 적용하며 현재 실행은 별도 중지 버튼으로 제어합니다.

문서를 연 상태에서는 대화·입력창이 같은 왼쪽 열에 남고 문서가 오른쪽 높이를 모두 사용합니다. 화면 폭이 좁으면 실행 수치는 3열 격자로 접히며, 엔진 압축 요약·출력 한도 메모는 EngineNotes를 통해 작업 내역에서만 펼칩니다(원본 기록은 유지).

대화 기록은 임시 선택 패널입니다. 대화 선택 후 닫히고, 열 때 작업 내역·문서와 동시에 본문 공간을 나누지 않습니다. 데스크톱에서도 Escape·키보드 초점 순환을 지원합니다. 대화 보관은 기록 패널에 두며 작업 중인 대화는 보관할 수 없습니다. 본문 문서 링크는 공통 텍스트 링크 스타일로 표시합니다.

대화 기록의 이름 바꾸기는 해당 행에서 입력·저장·취소합니다. session/rename API가 성공하면 목록과 헤더 제목만 갱신하며 선택 대화·기록·초안은 유지합니다.

실행 수치는 RuntimeMetrics.tsx, 실행 버튼은 HeaderActions.tsx로 분리했습니다. 모델 옆에 여섯 항목을 같은 크기의 작은 라벨·값으로 정렬하고 미수신 값은 —로 표시합니다. 모델명 옆의 실행 중·불러오는 중·미실행·연결 오류는 백엔드가 보고한 모델 상태입니다. 대화·작업 패널은 기본 닫힘이며 자료가 없는 수치를 임의 계산하지 않습니다.

읽기 모드는 입력창의 스위치로 켜고 끕니다. 전송·재개 요청의 read_only 값이 해당 작업에 적용되며, 기존 작업 환경의 권한 기본값보다 우선합니다. 작업 중에도 다음 요청의 스위치는 바꿀 수 있습니다. 선택은 브라우저에 기억하고 시스템 프롬프트 저장과 분리합니다.

데스크톱 작업 내역·문서는 왼쪽 경계를 드래그해 폭을 조절합니다. 방향키 조절·더블클릭 기본 폭 복원·각 패널의 폭 기억을 지원합니다. 모바일에서는 전체 폭으로 표시하며 크기 조절 손잡이를 숨깁니다.

ThinkingControl.tsx·useThinking.ts는 읽기 모드 옆에서 Thinking 자동/켜기/끄기를 선택합니다. 로컬 모델에만 표시하고 모델별 선택을 브라우저에 기억합니다. 전송·재개 직전에 기존 /api/ai_agent/Hermes/settings에 thinking_mode를 저장한 뒤 chat을 호출합니다. 실행 중 선택은 다음 요청에 적용하며 진행 중 작업과 모델 적재 상태는 변경하지 않습니다. 원본 request_overrides 연결은 [백엔드 모델 안내](../../backend/models/README.md)를 따릅니다.

2026-10-18 확인: TypeScript·Vite 빌드, 모의 API 브라우저 검사 29개 통과. Thinking 선택 후 전송·작업 중 다음 값 변경·새로고침 복원·390px 가로 넘침 없음을 검사했습니다. 실제 1440px 화면에서 읽기 모드 옆 Thinking 끄기와 JavaScript 오류 0건을 확인했고 390px도 표시·넘침 없음을 확인했습니다. 이번 UI 이동은 백엔드·모델 재시작 없이 프론트만 적용했으며 실제 추론 비교 검사는 추가 실행하지 않았습니다.

AppTabs.tsx는 원본 회사 현황·업무 실행 기록 UI를 유지하며 총괄 대화는 일반 Hermes 영구 세션으로 연결합니다. CompanyConversation.tsx는 사업 기록·승인만 조회합니다. Chat.tsx의 전송·도구 승인·중지·측정·Goal/Loop는 일반 대화와 같은 네이티브 API를 사용하며 회사 전용 전송 루프/측정 폴링을 만들지 않습니다.

회사 대화 선택은 projects/conversation action=session으로 동일한 native 세션을 열고 최초 과거 기록만 SessionDB에 이관합니다. 기존 회사 DB의 과거 메시지는 백업으로 남고 새 메시지는 native SessionDB에만 저장됩니다. 초안·첨부·Thinking·읽기 모드·자동 실행·작업 내역·여섯 측정값을 모두 유지합니다. 한 번/목표/반복 모드 변경도 같은 총괄 세션에서 가능합니다. 기존 일반 대화도 그대로 사용합니다.

사업 관리 패널은 기존 Panel/PanelResizeHandle과 승인/보류 UI를 유지합니다. 소유자 승인 후 같은 Hermes 세션의 Goal 실행으로 이어가며 고정 직원 순서를 만들지 않습니다. 승인된 로컬 제작과 외부 서비스 공개를 구분합니다. 원본 현황/기록의 모델 표시는 부모가 공유하는 실제 선택 모델 상태입니다. 모델 설정을 복제하지 않습니다.

2026-10-20 확인: TypeScript 통과. 관련 backend 회귀 64개 통과(원본 엔진 첫 목표 전달·동일 세션 터미널 경로 전환·회사 API 오류 사유/토큰 비노출 포함). 모의 API 브라우저 검사에서 대화/Goal/Loop·승인·초안·1440/390px를 확인했습니다. 별도 실제 서버/선택 모델 화면에서 동일 총괄 세션·실제 tok/s·사업 관리 패널·JavaScript 오류 0건·가로 넘침 없음을 확인했습니다. 자료는 runtime/ai_agent/Hermes/verification/workspace-tabs/의 native-ui-result.json(모의), native-real-ui.json(실제)입니다.

제품 실행 검증: 선택된 Ornith가 실제 의존성 설치·소스 수정·최초 Vite 빌드(exit 0)를 수행했습니다. 생성물의 타입 오류·계산 및 CSV/저장/인쇄 누락은 Codex가 직접 보완했습니다. 보완한 로컬 견적 앱은 계산/CSV/저장 검사 12개, 타입 검사를 포함한 빌드, 실제 브라우저 8개 시나리오(390px 포함)를 통과했습니다. 제품 workspaces/venture_cb169c20567f6fd2/verification/에 자료를 둡니다. 모델 단독 무개입 완성·외부 배포·결제·매출을 입증한 것은 아닙니다. 학습 메뉴/가중치 학습은 실행 경로 다음의 별도 작업입니다.

회사 현황·업무 기록은 Hermes 상위 탭에만 연결합니다. 사업 관리의 독립 제품 보기는 승인된 작업 폴더의 dist/index.html이 있을 때 로컬 결과를 엽니다. 외부 공개·결제 연결 상태와 구분하며 제작되지 않은 제품 링크는 만들지 않습니다.

Hermes 상위 탭은 대화 / 회사 현황 / 업무 실행 기록입니다. 총괄 전용 대화 탭은 제거했습니다. 마지막으로 고른 Hermes 대화를 유지하며 총괄 세션으로 강제 이동하지 않습니다. 입력창의 대화 대상 선택에서 AI 총괄을 선택할 수 있습니다. 실제 브라우저에서 일반 대화 선택 유지·입력창에서 총괄 선택·중복 탭 없음·결과물 버튼 유지를 확인했습니다. 기존 대화 기록은 보존합니다. 상단에는 사업 관리 열기·접기 버튼을 유지하고 기존 제품은 사업 관리에서 열고 대화 아래 상시 결과물 카드는 표시하지 않습니다. 데스크톱에서도 패널은 자동으로 열지 않습니다. 이전 확인의 두 헤더 버튼 구성은 현재 사용하지 않습니다. 2026-10-20 현재 TypeScript·Vite 빌드와 기존 설치 화면에서 사업 관리 버튼 하나로 열기·접기, 패널 내부 중복 제목·X 없음, 일반 대화의 결과물 카드 없음, 사업 관리의 EstimateAI 제품 링크 HTTP 200(대화 아래 상시 카드는 제거), Pretendard·공통 brand 배경 적용을 확인했습니다. 모델 호출·새 제품·검사 전용 파일은 만들지 않았습니다.

CEO 보고는 기본적으로 결과·막힌 점·대표의 결정 요청으로 제한합니다. 개발 파일/폴더/Git 상태를 자동으로 나열하지 않습니다. 요청 없는 Git 쓰기 시도는 기존 도구 승인 UI를 사용하며 내부 업무 기록은 그대로 보존합니다.

회사 초안 UX는 고정 원본 owner.html의 항목 카드/승인 확인 흐름을 기준으로 복구했습니다. 문제·제품·가격 가설·실험 계획을 펼쳐 보여주며 일반 대화를 바꾸지 않습니다. 총괄 세션의 초안은 사업 관리 버튼으로 열어 확인하며, 사업 승인 버튼의 확인창을 취소하면 실행 요청을 보내지 않습니다. 확인 후 승인한 경우에만 기존 단일 API/같은 native 세션의 제작 실행으로 이어집니다. 외부 공개·결제·지출을 승인한 것으로 취급하지 않습니다.

현재 확인: 원본 web_search_tool의 키 없는 검색 성공(결과 2건), TypeScript 통과, 실제 브라우저의 원본 회사 화면·초안·승인 확인창 취소 시 실행 없음·확인 후 동일 세션 실행·1440/390px 넘침/JS 오류 없음을 확인했습니다. 브라우저 검사는 API 픽스처이며 실제 모델 호출은 0회입니다. CEO의 실제 뉴스/사업 대화 판단은 별도 실사용 확인 대상입니다.

ChatGPT · Codex 모델 선택은 기존 대화/총괄 공통 설정을 사용합니다. model_connection 상태가 있으면 외부 모델/로그인 필요를 표시하며, 이전 서버·검사 픽스처에서는 기존 로컬 상태 표시를 유지합니다. 클라우드 작업에 보관 중인 로컬 모델의 슬롯 속도를 표시하지 않습니다.
ChatGPT 모델이면 입력창의 Thinking 위치에 서버가 광고한 추론 수준 선택을 표시합니다. useThinking이 현재 모델의 원본 카탈로그를 읽고 다음 요청 직전 기존 settings API에 모델별 선택을 저장합니다. 로컬 GGUF의 Thinking 자동/켜기/끄기 동작은 유지합니다. ReasoningSelect는 모델 설정 화면과 같은 컴포넌트입니다.

사업 관리 수정 확인: 기존 설치 화면에서 사업 초안과 승인·수정 안내가 표시되고 고객 요청·결제 매출 항목이 없음을 확인했습니다. 기존 승인 프로젝트 1개·실제 결과물 1개를 표시하며 준비 수는 projects/conversation의 progress.ready_products를 사용합니다. TypeScript·Vite 빌드 및 서버 적용 완료. 새 초안·제품·검사 파일·모델 추론은 생성하지 않았습니다.

진행 표시와 중간 메시지: 전송·중지 버튼을 분리하고 실행 중 Enter/전송은 기존 /chat/steer API로 전달합니다. native redirect가 현재 모델 요청만 전환하거나 도구 경계에서 steer로 전달하며 전체 작업을 중지하지 않습니다. 실행 방식·Thinking·읽기 모드의 변경은 기존처럼 다음 실행에 적용합니다. assistant의 중간 설명은 도구 호출이 붙어도 대화에 보존하고, 실제 도구 단계는 접을 수 있는 실행 과정으로 표시합니다. 검증된 파일 쓰기·수정 결과는 기존 GeneratedFiles→DocumentLink로 바로 열 수 있습니다. 레이아웃 단계에서 자동 스크롤을 맞추고 브라우저 자동 앵커와 충돌하지 않도록 합니다. 원본 영어 반복 실패 안내는 화면에서 한국어로 표시하되 원문 DB는 바꾸지 않습니다.

2026-10-20 이번 수정 확인: 기존 총괄 대화에서 상시 제품 배너 0개, 사업관리 안의 기존 제품 카드 1개를 실제 화면에서 확인했습니다. TypeScript·Vite 빌드 및 백엔드 구문 확인 후 서버에 적용했습니다. 기존 총괄 세션의 실제 Instinct 확인 요청 중 추가 지시를 전송해 동일 실행의 owner_steer 이벤트 수신과 입력창 비움을 확인했습니다. 새 제품·설치본·검사 파일은 만들지 않았습니다. 새 사업 초안 생성과 반복 실패의 재발 동작은 이번 확인에서 실행하지 않았습니다.

추가 지시는 원본 display_kind=steer인 사용자 메시지에서만 제어용 표식을 숨기며 원문 DB는 보존합니다. 위 실제 요청은 78초 뒤 완료됐습니다. 추가 지시 수신은 확인했으나 로컬 모델의 검색 효율과 답변 간결성이 해결됐다는 의미는 아닙니다.

2026-10-21 표시 수정: 같은 세션을 초기화 효과가 다시 선택하며 비우지 않도록 하고, 늦게 도착한 과거 조회 응답은 최신 조회를 덮어쓰지 못하게 합니다. 도구 시작 때 진행 문장을 지우지 않고 다음 생성 블록 시작까지 유지하며, DB의 마지막 assistant 문장과 같으면 스트리밍 중복만 숨깁니다. 원본 대화와 저장 DB는 변경하지 않습니다.

동일 기존 대화의 실제 웹 확인 중 화면 메시지는 306→307→308→309개로 유지·증가했고 일시적으로 빈 대화가 되거나 메시지 수가 줄어드는 현상은 관찰하지 않았습니다. 새 메시지 시작 시 과거 조회를 무효화하며 대화 전환 조회의 세대는 전환 후에 잡습니다. 임의 지연 API/가짜 세션을 만들지 않았으므로 모든 네트워크 지연 순서를 재현한 검사는 아닙니다.

## 실시간 회의

용도: MeetingRoom.tsx가 역할별 실제 발언을 대화처럼 보여주고 AppTabs.tsx가 새 회의/재검토 시작 시 해당 회의실로 전환합니다. 회의 안건은 team_meeting start 직후 기존 DB에 등록됩니다. Chat.tsx의 같은 총괄 세션/status/steer를 사용하며 새 하네스나 대화 DB를 만들지 않습니다.

발언은 원본 Hermes 독립 자식 에이전트의 실제 스트림입니다. 현재 발언은 공통 status의 meeting에서, 안건·저장 발언·직군·초안은 projects/conversation action=meetings에서 받습니다. 실제 source_session_id를 보존하고 완료된 발언을 다음 발언이나 결론으로 덮어쓰지 않습니다. 예전 저장 회의록은 원래 기록대로 보존합니다. 총괄이 참가자와 질문·재반론을 선택하며 고정 직군 순서는 없습니다.

입력창은 실행 중 chat/steer에, 종료 후 같은 meeting_id의 재검토 chat에 연결됩니다. 대표 메시지도 실제 회의에 기록합니다. 초안 검토 버튼은 기존 총괄 대화의 사업관리 패널을 열 뿐 승인하지 않습니다. 재검토 중에는 기존 초안을 revising으로 잠그고 같은 ID로 수정안을 재제출합니다. 대상 연결 실패 시 일반 대화로 잘못 전송하지 않도록 차단하며 입력은 보존합니다.

실제 확인(2026-10-21): 기존 설치본/총괄/로컬 Ornith에서 실시간 개인 AI 비서 안건을 등록하고 회의실 자동 전환을 확인했습니다. CPO 199→306자, QA 5→406자의 발언 스트림을 관찰했고, CTO·CMO·CFO·CS·QA가 앞선 실제 발언을 받아 독립 검토했습니다. 대표의 중간 지시도 같은 회의에 수신됐습니다. 첫 실행은 132.8초 후 총괄 결론과 승인 대기 초안을 실제 제출했습니다. 제품 제작·결제·외부 공개·시장 검증 결과가 아닙니다.

재검토 실제 확인: 같은 안건/같은 초안 ID를 유지하고 revising→pending 전환을 확인했습니다. CPO가 앞선 CTO 우려에 답하고 CTO가 재반론한 실제 위임 두 번을 추가했으며 제품·검증계획·고객·가격 필드가 수정됐습니다. 두 번째 실행 63.2초, 자식 포함 원본 API 카운터 8회입니다. 총 8개 실제 자식 세션의 source=subagent와 동일 parent_session_id를 확인했고 일반 대화 목록에는 노출되지 않습니다. 초안 버튼으로 기존 사업관리 패널이 열리는 것, 390px 가로 넘침 없음, 브라우저 JS 오류 0개를 확인했습니다. 소유자 승인은 누르지 않았고 제품/결제/공개는 실행하지 않았습니다.
