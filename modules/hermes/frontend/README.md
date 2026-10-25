# 헤르메스 프론트엔드

용도: Hermes 화면 컴포넌트·공통 UI 연결과 검증 범위를 안내합니다.

대화가 전체 작업 영역을 사용합니다. 집중 모드는 플랫폼 헤더와 메뉴도 접어 화면 전체를 사용합니다. 대화 헤더에서 세션·모델·새 대화·작업 내역에 접근합니다. 왼쪽 AI 에이전트 메뉴에는 헤르메스 진입점 하나를 표시합니다. 대화 오른쪽 톱니바퀴 설정 버튼을 누르면 대화·모델·작업 환경·MCP·스킬·시스템 프롬프트·개별 프롬프트 상단 탭으로 이동하며, 기존 settings/ 화면과 주소를 그대로 재사용합니다. 설정 주소는 사이드바에서만 숨기고 직접 접속·뒤로가기·새로고침을 유지합니다.

플랫폼 상위 콘텐츠의 최대 너비도 이 화면에서 해제해 양옆 회색 띠가 생기지 않게 합니다. 작업 기록은 오른쪽 패널의 단계별 목록에 표시하며, 공백뿐인 답변은 빈 말풍선이나 복사 버튼을 만들지 않습니다. 입력칸은 도구 모음과 분리된 전체 폭에서 시작해 입력에 따라 늘어납니다.

## 파일 안내

- Hermes.tsx: 대화/설정 전환, 집중 모드, 선택 모델과 상태 조회.
- settings/agent-prompts/README.md: 조직 공통·총괄·회의 직원의 개별 지침 편집과 실제 적용 범위.
- 설정에서 모델을 바꾼 뒤 대화로 돌아오면 이동 경로와 관계없이 현재 모델을 다시 조회합니다. 열린 대화의 모델명·추론 선택이 이전 모델에 머무르지 않도록 연결합니다.
- chat/Chat.tsx: 세션·초안·전송·중지·승인 등 상태와 API 연결.
- chat/ChatHeader.tsx·SessionSidebar.tsx·ActivityPanel.tsx·ChatComposer.tsx·ChatWelcome.tsx: 공통 UI를 사용하는 역할별 표시 컴포넌트.
- chat/ChatStream.tsx: 연속 도구 호출 묶음, 실제 실행 수치와 타임라인.
- chat/MessageBody.tsx: Markdown/GFM 답변·코드·표·목록 표시와 복사. 원본 HTML은 실행하지 않습니다.
- ../../../frontend/src/tailwind.css: 공통 테마·디자인 값과 Tailwind 유틸리티 기반 레이아웃·반응형 스타일. 메뉴별 CSS는 불러오지 않습니다.
- ../../../frontend/src/ui/Primitives.tsx: Button·IconButton·Input·Select·Textarea 등 공통 UI.

설정을 열어도 대화가 유지됩니다. 초안은 세션별 브라우저 저장소에 남고, 위로 스크롤한 사용자를 강제로 마지막으로 이동시키지 않습니다. 모바일 패널은 배경 클릭·Escape로 닫고 포커스를 돌려줍니다. 작업/로딩 중에만 반복 조회합니다. 수치는 기존 엔진의 보고 값을 표시하며 미수신 값은 대기 상태로 표시합니다.

## 검증

실행 중인 로컬 서버에 적용한 뒤 UI 검사를 실행합니다. 검사는 Hermes API를 픽스처로 대체하며 실제 모델·도구·금융 주문을 실행하지 않습니다.

    npm exec --workspace frontend -- playwright test hermes-workspace.local-browser.spec.ts --project=local-browser --reporter=line

Markdown API: https://github.com/remarkjs/react-markdown / https://github.com/remarkjs/remark-gfm

현재 대화·Thinking 제어와 최신 UI 검사 범위는 [대화 안내](chat/README.md)를 따릅니다. 모델 추론 속도·도구 실측은 [백엔드 모델 안내](../backend/models/README.md)에 별도 기록합니다. 과거 UI 검사 개수를 현재 전체 기능 확인으로 취급하지 않습니다.

개별 프롬프트는 기존 공통 시스템 지침·조직·직원 원문 기본값과 사용자 설정을 구분해 표시합니다. 이름 행을 바꿔 저장하면 settings 이벤트를 통해 기존 회사 iframe도 이름을 갱신하며 회의는 같은 서버 이름 투영을 사용합니다. 상세 적용 범위는 settings/agent-prompts/README.md에 정리합니다.

공식 디자인 시스템의 공통 Tailwind 연결은 `official-vite.ts`가 담당합니다. 호스트는 Hermes 모듈이 있을 때만 이 플러그인을 로드하며, 모듈이 없는 독립 배포본의 빌드를 방해하지 않습니다. 기존 UI 구성과 테마 값은 유지합니다.
