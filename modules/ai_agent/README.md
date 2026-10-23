# AI 에이전트 중메뉴 소유 폴더

용도: 원본 AI 프로그램별 플랫폼 연결 소스·화면·패치·등록 정보를 한 중메뉴 안에서 관리합니다.

- [HermesOriginal/](HermesOriginal/README.md): backend·frontend·한국어 패치·module.json.
- [OpenClawOriginal/](OpenClawOriginal/README.md): backend·frontend·프레임 정책·module.json.
- 각 `backend/original/manager.py` → 중메뉴 `backend/manager.py` → 공통 `backend/ai_agent/manager.py` → `backend/register.py` 자동 등록 → 전체 총괄 → 단일 `/api`.
- 공식 원본 설치·업데이트·사용자 상태는 기존 `runtime/ai_agent/<중메뉴>/`를 유지합니다. 이 폴더가 원본 본체를 복제하지 않습니다.

호스트는 이 대메뉴/중메뉴 배치와 기존 `modules/<id>/` 배치를 함께 등록합니다. 기존 이식 Hermes·금융·REA와 외부 앱의 소유 폴더는 이번 두 중메뉴 통합으로 옮기지 않습니다.
