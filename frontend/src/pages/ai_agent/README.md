# AI 에이전트 대메뉴

AI 에이전트 화면 구성과 주소를 관리합니다. `ai_agent_menu_manager.ts` → `submenu_manager.ts` → 공통 Shell 등록 순서입니다.

- 헤르메스 대화: `#ai_agent/Hermes`
- 모델: `#ai_agent/Hermes/models`
- MCP: `#ai_agent/Hermes/mcp`
- 스킬: `#ai_agent/Hermes/skills`
- 시스템 프롬프트: `#ai_agent/Hermes/prompt`

`agent_navigation.ts`가 메뉴 이름·설정 구분·주소 이동을 공유합니다. 다섯 메뉴는 같은 Hermes 작업공간 컴포넌트를 사용해 이동 중에도 대화·초안을 유지합니다. 새로고침·브라우저 뒤로가기도 주소에 맞는 화면을 복원합니다. 기존 query 방식 설정 주소도 읽을 수 있습니다.

기능 구현은 [Hermes/README.md](Hermes/README.md)와 [settings/README.md](Hermes/settings/README.md)에 있습니다. API는 기존 단일 `/api`의 `ai_agent/Hermes/*`를 공유하며 서버·엔진을 메뉴별로 복제하지 않습니다.

확인: `frontend/tests/hermes-workspace.local-browser.spec.ts`에서 실제 메뉴 주소 이동·복원·입력 보존을 검사합니다. 모델 실행·학습·매매를 시작하는 탐색은 하지 않습니다.
