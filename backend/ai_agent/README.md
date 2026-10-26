# AI 에이전트 대메뉴

용도: AI Agent 대메뉴 아래 각 중메뉴 백엔드를 취합하고 메뉴별 frontend와 runtime 연결을 안내합니다.

- `manager.py`: [헤르메스 원본](../../backend/ai_agent/hermes_original/README.md)과 [OpenClaw 원본](../../backend/ai_agent/openclaw_original/README.md) 중메뉴 매니저를 import합니다.
- 각 중메뉴의 `backend/original/manager.py`가 원본 화면 소메뉴를 담당합니다. 중메뉴 → 대메뉴 → 모듈 자동 등록 → 전체 메뉴 총괄 → 단일 `/api`로 연결합니다.
- 백엔드 구현은 `backend/ai_agent/<중메뉴>/`, 프론트 구현은 `frontend/src/pages/ai_agent/<중메뉴>/`에 둡니다. 각 backend `module.json`이 대응하는 프론트 register와 단일 `/api` 등록을 연결합니다. `modules/ai_agent/`에는 구현을 두지 않습니다.
- [기존 이식 Hermes](../../backend/ai_agent/choki/README.md)는 기존 모듈의 `backend/` 구현·전용 환경·등록을 유지합니다. `platform_modules.mount_namespaces()`가 `ai_agent.choki` 소스를 연결합니다.
- 공식 원본 체크아웃은 각 `runtime/ai_agent/<중메뉴>/source/`, 사용자 설정은 `home/`, 도구는 `tools/`입니다. 기존 공식 설치·업데이트 경로를 유지하며 원본 Git 의존성과 플랫폼 연결 코드를 구분합니다.

실제 실행과 미확인 범위는 각 중메뉴 README를 따릅니다. 다른 PC 설치·원본 업데이트·모델 응답을 이번 디렉터리 정리의 성공으로 표시하지 않습니다.

[토큰 최적화](../../backend/ai_agent/token_optimizer/README.md)는 실제 Token Optimizer·RTK 집계를 제공하는 독립 중메뉴입니다. manager.py는 중메뉴별 매니저를 요청 시 import합니다.
