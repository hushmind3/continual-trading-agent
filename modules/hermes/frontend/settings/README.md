# 헤르메스 설정 화면

용도: 대화 오른쪽 설정에서 플랫폼 상단 탭으로 공식 기능과 조직 설정을 관리합니다.

- `Settings.tsx`·`../agent_navigation.ts`: 상단 탭·주소·방문한 화면 상태를 관리합니다. 대화는 숨겨 유지하고 새 왼쪽 메뉴를 만들지 않습니다.
- `official/OfficialWorkspace.tsx`: 공식 React 페이지·프로필·플러그인을 재사용합니다. MCP·스킬과 고급 모델 설정은 이 화면을 사용합니다. 전체 기능에서 대화 기록·파일·사용량·로그·예약·플러그인·메신저·프로필·장기기억을 포함한 전체 설정·인증·시스템을 엽니다.
- `official/transport.ts`와 `../official-vite.ts`: 같은 /api의 매니저 등록 통로로 실제 공식 HTTP/WebSocket을 연결합니다. 전체 기능 코드를 iframe·모의 결과로 대체하지 않습니다.
- `prompt/SystemPrompt.tsx`·`agent-prompts/AgentPrompts.tsx`·`workspace/WorkspaceSettings.tsx`: 기존 플랫폼 조직·직원 프롬프트·작업 환경을 보존합니다.
- `models/ModelSettings.tsx`: 주 모델은 원본 공용 선택기로 고르고 보조 모델·협업은 고급 설정에서 엽니다. ReasoningSelect는 기존 대화 입력창과 공유하는 실제 카탈로그 기반 추론 선택기입니다.

스타일은 공통 frontend/src/tailwind.css의 플랫폼 색상·Pretendard 글꼴을 사용합니다. 메뉴·버튼·안내는 한국어이며 실제 모델·프로필·설정 키는 식별자로 보존합니다. 공식 기본 프로필의 대화 기록 열기는 같은 기존 채팅으로 돌아가며 대화를 복제하지 않습니다.

현재 TypeScript·운영 빌드와 실제 기본 설정 화면 표시·브라우저 오류 없음은 확인했습니다. 최종 프로토콜·화면 검증은 진행 중이며 모든 외부 인증·유료 기능 실행을 확인했다는 뜻은 아닙니다.
