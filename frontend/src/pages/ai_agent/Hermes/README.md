# 헤르메스

대화가 전체 작업 영역을 사용합니다. 집중 모드는 플랫폼 헤더와 메뉴도 접어 화면 전체를 사용합니다. 대화 헤더에서 세션·모델·새 대화·작업 내역에 접근합니다. AI 에이전트 대메뉴는 대화·모델·작업 환경·MCP·스킬·시스템 프롬프트 소메뉴를 등록하고 기존 settings/ 구현을 각 주소에서 재사용합니다.

플랫폼 상위 콘텐츠의 최대 너비도 이 화면에서 해제해 양옆 회색 띠가 생기지 않게 합니다. 작업 기록은 오른쪽 패널의 단계별 목록에 표시하며, 공백뿐인 답변은 빈 말풍선이나 복사 버튼을 만들지 않습니다. 입력칸은 도구 모음과 분리된 전체 폭에서 시작해 입력에 따라 늘어납니다.

## 파일 안내

- Hermes.tsx: 대화/설정 전환, 집중 모드, 선택 모델과 상태 조회.
- chat/Chat.tsx: 세션·초안·전송·중지·승인 등 상태와 API 연결.
- chat/ChatHeader.tsx·SessionSidebar.tsx·ActivityPanel.tsx·ChatComposer.tsx·ChatWelcome.tsx: 공통 UI를 사용하는 역할별 표시 컴포넌트.
- chat/ChatStream.tsx: 연속 도구 호출 묶음, 실제 실행 수치와 타임라인.
- chat/MessageBody.tsx: Markdown/GFM 답변·코드·표·목록 표시와 복사. 원본 HTML은 실행하지 않습니다.
- ../../../tailwind.css: 공통 테마·디자인 값과 Tailwind 유틸리티 기반 레이아웃·반응형 스타일. 메뉴별 CSS는 불러오지 않습니다.
- ../../../ui/Primitives.tsx: Button·IconButton·Input·Select·Textarea 등 공통 UI.

설정을 열어도 대화가 유지됩니다. 초안은 세션별 브라우저 저장소에 남고, 위로 스크롤한 사용자를 강제로 마지막으로 이동시키지 않습니다. 모바일 패널은 배경 클릭·Escape로 닫고 포커스를 돌려줍니다. 작업/로딩 중에만 반복 조회합니다. 수치는 기존 엔진의 보고 값을 표시하며 미수신 값은 대기 상태로 표시합니다.

## 검증

실행 중인 로컬 서버에 적용한 뒤 UI 검사를 실행합니다. 검사는 Hermes API를 픽스처로 대체하며 실제 모델·도구·금융 주문을 실행하지 않습니다.

    npm exec --workspace frontend -- playwright test hermes-workspace.local-browser.spec.ts --project=local-browser --reporter=line

Markdown API: https://github.com/remarkjs/react-markdown / https://github.com/remarkjs/remark-gfm

검증: AI 소메뉴 등록·주소 복원·모바일 입력 폭·문서/대화 열 분리·내부 요약 분리 등 UI 20개, TypeScript·Vite 빌드 통과. 실제 로컬 배포 화면에서도 소메뉴와 모델 화면 이동을 확인했습니다. 모델 추론은 이번 UI 변경 검증에서 시작하지 않았습니다.
