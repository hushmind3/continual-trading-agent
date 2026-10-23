# AI 에이전트 대메뉴

용도: 원본 AI 프로그램의 중메뉴를 취합하고 기존 이식 Hermes와의 소스 경계를 안내합니다.

- `manager.py`: [헤르메스 원본](../../modules/ai_agent/HermesOriginal/backend/README.md)과 [OpenClaw 원본](../../modules/ai_agent/OpenClawOriginal/backend/README.md) 중메뉴 매니저를 import합니다.
- 각 중메뉴의 `backend/original/manager.py`가 원본 화면 소메뉴를 담당합니다. 중메뉴 → 대메뉴 → 모듈 자동 등록 → 전체 메뉴 총괄 → 단일 `/api`로 연결합니다.
- 원본별 backend·frontend·한국어 패치·module.json은 `modules/ai_agent/<중메뉴>/` 한 폴더가 소유합니다. 그 안의 `backend/register.py`가 이 대메뉴 매니저를 통해 자동 등록합니다. 이 공통 폴더에 중메뉴 구현을 복제하지 않습니다.
- [기존 이식 Hermes](../../modules/hermes/README.md)는 기존 모듈의 `backend/` 구현·전용 환경·등록을 유지합니다. `platform_modules.mount_namespaces()`가 `ai_agent.Hermes` 소스를 연결합니다.
- 공식 원본 체크아웃은 각 `runtime/ai_agent/<중메뉴>/source/`, 사용자 설정은 `home/`, 도구는 `tools/`입니다. 기존 공식 설치·업데이트 경로를 유지하며 원본 Git 의존성과 플랫폼 연결 코드를 구분합니다.

실제 실행과 미확인 범위는 각 중메뉴 README를 따릅니다. 다른 PC 설치·원본 업데이트·모델 응답을 이번 디렉터리 정리의 성공으로 표시하지 않습니다.
