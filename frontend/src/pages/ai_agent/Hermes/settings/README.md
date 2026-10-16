# AI 에이전트 설정 화면 연결

모델·작업 환경·MCP·스킬·시스템 프롬프트의 기존 구현을 각 소메뉴에서 재사용합니다. `Settings.tsx`는 주소에 맞는 설정 기능만 표시하며, 중복 왼쪽 설정 메뉴를 만들지 않습니다. 상위 `../../agent_navigation.ts`가 화면 목록·이동을 관리합니다.

상위 대메뉴 주소는 [../../README.md](../../README.md)에 있습니다. 대화로 돌아가기·화면 선택·브라우저 뒤로가기·새로고침을 지원합니다. 대화는 숨겨 둔 채 유지하며 메뉴 이동 자체가 모델이나 도구를 실행하지 않습니다.

기능 코드: models/ModelSettings.tsx, mcp/McpPage.tsx, skills/Skills.tsx, prompt/SystemPrompt.tsx. workspace/WorkspaceSettings.tsx는 작업 폴더·도구·반복 한도를 별도 소메뉴로 표시합니다. useAgentSettings.ts는 설정 조회·실패·재시도를 공유합니다. 모델 설정은 서버 연결 필드만, 작업 환경은 workspace/toolsets/max_iterations만 저장합니다. 각 기능 API와 권한·저장 위치는 각 README를 따릅니다.
