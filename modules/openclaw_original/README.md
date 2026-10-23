# OpenClaw 원본 메뉴

이 문서는 프로젝트 플랫폼 AI 에이전트 메뉴에 연결한 공식 OpenClaw 원본의 실행과 사용 방법을 설명합니다.

- 화면: `frontend/Original.tsx`; 메뉴 등록은 `frontend/register.ts`와 `module.json`에서 합니다.
- 실행 API: `backend/manager.py`가 단일 `/api` 경로에 상태·시작·중지 작업을 등록하고, `backend/runtime.py`가 전용 Gateway 프로세스를 관리합니다.
- 원본 실행: `backend/launch.py`가 `runtime/ai_agent/OpenClawOriginal/source/`의 공식 CLI와 분리된 `home/` 설정을 사용합니다.
- 화면: OpenClaw는 기본적으로 화면 삽입을 차단합니다. `backend/frame_policy.mjs`는 Gateway HTML 문서의 CSP를 8766 출처만 허용하도록 제한하고 `X-Frame-Options`를 해당 문서에서만 제거합니다. Gateway 기본 경로와 원본 포트를 유지해 기존 브라우저 인증 저장소를 재사용합니다. 프론트엔드는 OpenClaw 공식 대시보드의 기본 화면을 공통 작업 화면 iframe에 표시합니다. 모델 제공자가 설정되지 않았다면 OpenClaw 자체 첫 실행 설정 화면이 표시됩니다.
- 사용: 8766의 `AI 에이전트 → OpenClaw 원본 → 원본 화면`에서 원본 대시보드를 사용합니다. Gateway 토큰은 최초 연결 때 OpenClaw 원본 포트에서 한 번 입력하면 됩니다. 모델 응답을 받으려면 대시보드의 모델 설정에서 제공자를 연결해야 합니다.
- 확인: 메뉴의 실행 상태를 확인하고 실제 대시보드가 iframe 안에서 `연결됨`으로 열리는지 봅니다. 상태 API는 `/api?operation=ai_agent/OpenClawOriginal/status&payload={}`입니다.

현재 확인 결과: Gateway 실행 중이며 OpenClaw UI 연결 상태와 iframe 삽입 정책을 확인했습니다. Codex OAuth 로그인과 `openai/gpt-6-luna` 선택을 OpenClaw 화면에서 저장한 뒤 플러그인 교체 대기 때문에 재연결이 멈춰 Gateway를 재시작했습니다. 재시작 후 UI는 `연결됨`이고 GPT-6-Luna가 표시됩니다. 실제 모델 응답은 아직 확인하지 않았습니다.
