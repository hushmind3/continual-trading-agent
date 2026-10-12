# 백엔드 구조 안내

먼저 해당 폴더 README를 읽고 필요한 진입점만 확인합니다.

| 담당 | 폴더/파일 | 먼저 확인할 문서 |
| --- | --- | --- |
| 메인 프레임워크 | finrl/ | [FinRL 안내](finrl/README.md) |
| 보조 프레임워크 | finrl_trading/ | [FinRL-Trading 안내](finrl_trading/README.md) |
| 공통 상태·실행 관리 | platform/ | [공통 관리 안내](platform/README.md) |
| 단일 API·React 제공 | web_api.py | 상태 조회와 명령 중계 진입점 |
| 별도 작업 프로세스 | job_worker.py, official_cli.py | 등록된 작업 실행·종료 기록 |
| 공통 경로 | __init__.py | 프로젝트 ROOT만 정의 |

## 연결 원칙

- FinRL·SB3가 알고리즘 선택·생성·학습을 담당합니다.
- FinRL-Trading은 기존 저장·추가 수집·전략·비중 평가를 보조합니다.
- React는 단일 /api를 호출합니다. 상태와 작업 관리는 SystemOperations가 공유합니다.
- 실행 코드 import는 stockrl.finrl 또는 stockrl.finrl_trading의 실제 모듈을 사용합니다.
- 모델·Replay·데이터·계좌·인증은 이 소스 폴더의 정리 대상이 아닙니다.
