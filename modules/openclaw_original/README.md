# OpenClaw 원본 메뉴

이 문서는 프로젝트 플랫폼 AI 에이전트 메뉴에 연결한 공식 OpenClaw 원본의 실행과 사용 방법을 설명합니다.

- 화면: `frontend/Original.tsx`; 메뉴 등록은 `frontend/register.ts`와 `module.json`에서 합니다.
- 실행 API: `backend/manager.py`가 단일 `/api` 경로에 상태·시작·중지 작업을 등록하고, `backend/runtime.py`가 전용 Gateway 프로세스를 관리합니다.
- 원본 실행: `backend/launch.py`가 `runtime/ai_agent/OpenClawOriginal/source/`의 공식 CLI와 분리된 `home/` 설정을 사용합니다.
- 화면: OpenClaw는 기본적으로 화면 삽입을 차단합니다. `backend/frame_policy.mjs`는 Gateway HTML 문서의 CSP를 8766 출처만 허용하도록 제한하고 `X-Frame-Options`를 해당 문서에서만 제거합니다. `backend/launch.py`는 공식 대시보드를 8766 안에서 바로 쓰도록 Gateway 인증을 끄되, 바인딩을 로컬 루프백으로 고정해 다른 장치나 네트워크에서 접속할 수 없게 합니다. 프론트엔드는 OpenClaw 공식 대시보드의 기본 화면을 공통 작업 화면 iframe에 표시합니다. 모델 제공자가 설정되지 않았다면 OpenClaw 자체 첫 실행 설정 화면이 표시됩니다.
- 원격 접속: Gateway는 루프백에 유지하고, Tailscale Serve를 통해 로그인된 기기에만 화면을 제공합니다. 프로젝트 실행기는 `TAILSCALE_SOCKET`으로 사용자 권한 Tailscale 데몬을 조회하며, 소켓 경로가 오래된 경우 `~/.tailscale-projectplatform.sock`을 사용합니다. `backend/launch.py`가 tailnet 출처를 허용하고 `frontend/Original.tsx`가 원격 화면에서 Gateway HTTPS 주소를 사용합니다.
- 사용: 이 Mac과 접속 기기 모두 같은 Tailscale 계정으로 로그인한 뒤 `tailscale serve --bg --https=443 http://127.0.0.1:8766` 및 `tailscale serve --bg --https=8443 http://127.0.0.1:19021`을 실행합니다. 원격 브라우저는 이 Mac의 `https://<기기이름>.<tailnet>.ts.net/` 주소를 사용합니다. 모델 응답을 받으려면 대시보드의 모델 설정에서 제공자를 연결해야 합니다.
- 확인: 메뉴의 실행 상태를 확인하고 실제 대시보드가 iframe 안에서 `연결됨`으로 열리는지 봅니다. 상태 API는 `/api?operation=ai_agent/OpenClawOriginal/status&payload={}`입니다.

현재 확인 결과: Gateway 기본 토큰 인증 때문에 별도 토큰 입력 화면이 나오는 문제를 수정했습니다. 8766의 시작 API로 Gateway를 다시 시작했고 상태는 `ready`입니다. 전용 OpenClaw 설정을 읽는 `health --json` 실행도 토큰 입력 없이 `ok: true`, `coreReady: true`를 반환했습니다. Tailscale 원격 접속은 기기 로그인 및 Serve 설정 후 확인합니다. 실제 모델 응답은 아직 확인하지 않았습니다.
