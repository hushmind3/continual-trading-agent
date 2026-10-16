# AI 에이전트 대메뉴

AI 에이전트 화면 구성과 주소를 관리합니다. `ai_agent_menu_manager.ts` → `submenu_manager.ts` → 공통 Shell 등록 순서입니다.

- 헤르메스 대화: `#ai_agent/Hermes`
- 모델: `#ai_agent/Hermes/models`
- 작업 환경: `#ai_agent/Hermes/workspace`
- MCP: `#ai_agent/Hermes/mcp`
- 스킬: `#ai_agent/Hermes/skills`
- 시스템 프롬프트: `#ai_agent/Hermes/prompt`

`agent_navigation.ts`가 메뉴 이름·설정 구분·주소 이동을 공유합니다. 여섯 메뉴는 같은 Hermes 작업공간 컴포넌트와 mountKey를 사용해 이동 중에도 대화·초안을 유지합니다. 새로고침·브라우저 뒤로가기도 주소에 맞는 화면을 복원합니다. 기존 query 방식 설정 주소도 읽을 수 있습니다.

기능 구현은 [Hermes/README.md](Hermes/README.md)와 [settings/README.md](Hermes/settings/README.md)에 있습니다. API는 기존 단일 `/api`의 `ai_agent/Hermes/*`를 공유하며 서버·엔진을 메뉴별로 복제하지 않습니다.

확인: `frontend/tests/hermes-workspace.local-browser.spec.ts`에서 실제 메뉴 주소 이동·복원·입력 보존을 검사합니다. 모델 실행·학습·매매를 시작하는 탐색은 하지 않습니다.

메뉴 계층: **AI 에이전트(대메뉴) → 헤르메스(중메뉴) → 대화·모델·작업 환경·MCP·스킬·시스템 프롬프트(소메뉴)**. section 메타데이터를 공통 NavigationTree가 표시합니다. OpenClaw를 추가할 때는 Hermes와 별도 section·작업공간·mountKey를 등록하며, 현재 OpenClaw 항목이나 엔진은 추가하지 않습니다.

2026-10-16 확인: TypeScript·Vite 빌드 성공, Hermes 브라우저 검사 24개 통과. 3단계 메뉴 접기·펼치기, 여섯 실행 수치, 모델 미실행 표시, 문서·첨부·설정 초안 보존을 확인했습니다. HTML 보고서는 채팅 옆에서 실제로 열어 확인했습니다. 프론트 독립 적용 완료. 실제 GGUF 추론·학습·매매는 이번 UI 검사에서 실행하지 않았습니다.
