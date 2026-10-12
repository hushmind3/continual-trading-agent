# 백엔드 구조 안내

먼저 해당 폴더 README를 읽고 필요한 진입점만 확인합니다.

큰 메뉴와 화면별 수정 위치는 [메뉴 연결 안내](MENU_MAP.md)를 먼저 확인합니다.

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

## 전체 메뉴 연결

menu_registry.py는 큰 메뉴 연결 파일 5개만 import하고, 각 파일은 3/6/1/2/3개의 작은 메뉴를 연결합니다. SystemOperations의 공통 상태·모델 캐시는 변경하지 않습니다. 메뉴 정보는 기존 단일 state의 menu_catalog 항목으로 제공합니다.

## 메뉴 등록과 실제 요청 분배

menu_registry.py는 큰 메뉴 연결 파일 5개만 import합니다. 각 큰 메뉴 연결 파일은 자기 아래 작은 메뉴만 연결합니다. 기존 API 핸들러를 메뉴별로 묶어 bind하고 dispatch하며 SystemOperations에 메뉴 연결을 추가하지 않습니다. 상태·모델·작업 관리는 기존 공통 관리자를 사용합니다.

등록된 화면·추가 기능·API 입력 계약은 단일 state의 menu_catalog 조회로 제공합니다. API 등록은 실제 실행 성공을 뜻하지 않습니다.

공식 보조 원본은 finrl_trading/upstream/입니다. 같은 프레임워크의 연결 코드와 구역을 공유합니다. 모듈·패키지 파일은 실제 경로로 중복 목록을 제거하며 실행 검사 없이 작은 메뉴에 등록합니다.
