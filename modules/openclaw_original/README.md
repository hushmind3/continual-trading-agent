# OpenClaw 원본 메뉴

용도: AI 에이전트 → OpenClaw 원본 → 원본 화면의 모듈 등록·React 화면·원격 접근과 확인 범위를 안내합니다.

실제 백엔드·설치·업데이트·소메뉴 계층은 [중메뉴 안내](../../backend/ai_agent/OpenClawOriginal/README.md)를 따릅니다. `backend/manager.py`는 대메뉴 매니저를 노출하는 자동 등록 연결입니다. 원본은 루트 `.gitmodules`의 고정 커밋으로 복원합니다.

- 화면: `frontend/Original.tsx`; 메뉴 등록은 `frontend/register.ts`와 `module.json`에서 합니다.
- 실행 API: `backend/ai_agent/OpenClawOriginal/original/manager.py`가 중메뉴·대메뉴 매니저를 통해 단일 `/api` 경로에 상태·시작·중지 작업을 등록하고, `backend/ai_agent/OpenClawOriginal/runtime.py`가 전용 Gateway 프로세스를 관리합니다.
- 원본 실행: `backend/ai_agent/OpenClawOriginal/launch.py`가 `runtime/ai_agent/OpenClawOriginal/source/`의 공식 CLI와 분리된 `home/` 설정을 사용합니다.
- 화면: OpenClaw는 기본적으로 화면 삽입을 차단합니다. `backend/ai_agent/OpenClawOriginal/frame_policy.mjs`는 Gateway HTML 문서의 CSP를 8766 출처만 허용하도록 제한하고 `X-Frame-Options`를 해당 문서에서만 제거합니다. Gateway는 루프백에만 바인딩하고, 원격 접속 시에는 8766의 로그인 쿠키를 검증합니다. 프론트엔드는 OpenClaw 공식 대시보드의 기본 화면을 공통 작업 화면 iframe에 표시합니다. 모델 제공자가 설정되지 않았다면 OpenClaw 자체 첫 실행 설정 화면이 표시됩니다.
- 원격 접속: 8766의 `backend/remote_access.py`가 원격 대시보드와 API에 공통 비밀번호 로그인을 요구합니다. 비밀번호와 쿠키 서명 키는 Git에 포함되지 않는 `runtime/platform/remote_access.json`에 최초 실행 시 생성됩니다. 직접 정하거나 변경하려면 프로젝트 루트에서 `.venv/platform/bin/python development/scripts/set_remote_password.py`를 실행합니다. OpenClaw Gateway의 HTTP·WebSocket도 같은 쿠키를 확인하며 비밀번호 변경을 바로 반영합니다. Gateway는 로컬 루프백에만 유지하고 외부 포트에 직접 바인딩하지 않습니다.
- 사용: Tailscale Funnel에서 HTTPS 443을 `127.0.0.1:8766`, HTTPS 8443을 `127.0.0.1:19021`에 연결하면 됩니다. 접속 기기에 Tailscale을 설치하지 않아도 브라우저에서 `https://<기기이름>.<tailnet>.ts.net/`을 열고 비밀번호를 한 번 입력하면 됩니다. 모델 응답을 받으려면 대시보드의 모델 설정에서 제공자를 연결해야 합니다.
- 확인: 원격 주소의 로그인 화면, 로그인 후 대시보드 API, OpenClaw 화면 및 WebSocket 연결을 확인합니다. 상태 API는 `/api?operation=ai_agent/OpenClawOriginal/status&payload={}`입니다.

현재 확인 결과: Gateway 기본 토큰 인증 때문에 별도 토큰 입력 화면이 나오는 문제를 수정했습니다. Gateway 상태는 `ready`이며, 전용 설정의 `health --json`은 토큰 입력 없이 `ok: true`, `coreReady: true`를 반환합니다. Funnel HTTPS 443·8443과 비밀번호 게이트를 켰고, 로컬에서 로그인·쿠키·API·Gateway 차단/허용 경로를 확인했습니다. 공인 DNS는 아직 반영되지 않아 외부 브라우저 접속은 미확인입니다. 실제 모델 응답도 아직 확인하지 않았습니다.

2026-10-24 로컬 정리 확인: 실제 백엔드를 `backend/ai_agent/`의 대메뉴·중메뉴·원본 화면 소메뉴 계층으로 정리하고 자동 등록 연결·문서·CLI·패치 경로를 맞췄습니다. 공식 원본 설치·업데이트 위치와 사용자 home·tools는 유지했습니다. 기존 설치본에서 시작·상태 ready·HTTP 200과 8766의 원본 iframe 본문 표시·JavaScript 오류 없음을 확인했습니다. Hermes Gateway도 실행 상태로 복구했고 활성 작업 0개·보류 프로필 없음이 확인됐습니다. 공식 업데이트·새 의존성 설치·다른 PC 설치·모델 추론은 이번 정리에서 실행하지 않았습니다.
