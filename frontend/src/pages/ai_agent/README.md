# AI 에이전트 대메뉴

AI 에이전트 화면 구성과 주소를 관리합니다. `ai_agent_menu_manager.ts` → `submenu_manager.ts` → 공통 Shell 등록 순서입니다.

- Choki 대화: `#ai_agent/choki`
- 모델: `#ai_agent/choki/models`
- 작업 환경: `#ai_agent/choki/workspace`
- MCP: `#ai_agent/choki/mcp`
- 스킬: `#ai_agent/choki/skills`
- 시스템 프롬프트: `#ai_agent/choki/prompt`

`agent_navigation.ts`가 메뉴 이름·설정 구분·주소 이동을 공유합니다. 여섯 메뉴는 같은 Hermes 작업공간 컴포넌트와 mountKey를 사용해 이동 중에도 대화·초안을 유지합니다. 새로고침·브라우저 뒤로가기도 주소에 맞는 화면을 복원합니다. 기존 query 방식 설정 주소도 읽을 수 있습니다.

기능 구현은 [Hermes 화면](./choki/README.md)과 [백엔드](../../../../backend/ai_agent/choki/README.md)에 있습니다. API는 기존 단일 `/api`의 `ai_agent/choki/*`를 공유하며 서버·엔진을 메뉴별로 복제하지 않습니다.

확인: `frontend/tests/hermes-workspace.local-browser.spec.ts`에서 실제 메뉴 주소 이동·복원·입력 보존을 검사합니다. 모델 실행·학습·매매를 시작하는 탐색은 하지 않습니다.

메뉴 계층: **AI 에이전트(대메뉴) → Choki(중메뉴) → 대화·모델·작업 환경·MCP·스킬·시스템 프롬프트(소메뉴)**. section 메타데이터를 공통 NavigationTree가 표시합니다. OpenClaw는 Choki와 별도 section·작업공간·mountKey를 사용하며, Hermes·OpenClaw 공식 원본은 각각 독립된 중메뉴로 등록되어 있습니다.

2026-10-16 확인: TypeScript·Vite 빌드 성공, Hermes 브라우저 검사 24개 통과. 3단계 메뉴 접기·펼치기, 여섯 실행 수치, 모델 미실행 표시, 문서·첨부·설정 초안 보존을 확인했습니다. HTML 보고서는 채팅 옆에서 실제로 열어 확인했습니다. 프론트 독립 적용 완료. 실제 GGUF 추론·학습·매매는 이번 UI 검사에서 실행하지 않았습니다.

헤르메스 원본은 별도 중메뉴 `#ai_agent/HermesOriginal`에 등록합니다. [원본 모듈](../../../../backend/ai_agent/hermes_original/README.md)의 register.ts가 전체 원본 dashboard를 엽니다. OpenClaw 원본도 별도 중메뉴 `#ai_agent/OpenClawOriginal`과 독립 mountKey로 등록하며 [원본 실행 안내](../../../../backend/ai_agent/openclaw_original/README.md)에 따라 전용 상태 폴더에서 공식 Control UI를 엽니다. 두 원본의 설정·대화·실행 상태는 분리하며 기존 Hermes 작업공간은 유지합니다.
