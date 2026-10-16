# Backend platform

| 위치 | 역할 |
| --- | --- |
| [stockrl/](stockrl/README.md) | 금융 대메뉴: 사용자 화면 5개 및 숨김 관리 메뉴 |
| [rea/](rea/README.md) | 독립 REA 프로젝트: program_analysis/, project_explorer/ |
| [modules/hermes/](../modules/hermes/README.md) | Hermes 프로그램: 엔진·채팅·모델·세션·MCP·스킬. 데이터는 runtime에 보존 |
| [platform_modules.py](platform_modules.py) | modules/*/module.json 탐색·Python 등록·실행 보호 훅 |
| [menu_registry.py](menu_registry.py) | 모듈 등록 정보를 취합하는 총괄 |
| [web_api.py](web_api.py) | 단일 /api 진입점; 총괄만 통해 기능 등록 |
| api_context.py, api_transport.py | 공유 HTTP 객체·요청 전달·React 제공 |
| runtime/rea/project_explorer/projects/ | 저장된 원본·추론 분석 결과; 실행 기능 등록 대상이 아니며 Git 제외 |

하위 기능 → 소메뉴 매니저 → 대메뉴 → 전체 메뉴 매니저 → API.
각 프로젝트와 작은 메뉴 README를 먼저 읽습니다. 새 프로젝트의 등록 규격은 [modules/README.md](../modules/README.md)입니다. 기능은 자기 매니저로 취합하며 중앙 파일에 프로젝트별 import를 추가하지 않습니다. 구조 이름은 영문 ASCII입니다.

Python 설치 메타데이터는 .venv/Lib/site-packages/continual_trading_agent-0.1.0.dist-info/에 있습니다. backend/의 같은 버전 egg-info는 setuptools 빌드 잔여물이어서 휴지통으로 이동했습니다. __pycache__/는 Python이 생성하는 캐시이며 대메뉴가 아닙니다.

## 런타임 소속

외부 HTTP 진입점은 단일 `/api`입니다. 소메뉴 모듈 → 대메뉴 매니저 → menu_registry 총괄의 import·등록 계층을 유지하며, 런타임은 아래 소유 메뉴에 저장합니다.

| 위치 | 소유 기능 |
| --- | --- |
| runtime/platform/ | 공통 서버·적용·감시 |
| runtime/finance/operation_control/ | 자동 운영·시세 수신·선택 정책 |
| runtime/finance/virtual_account_orders/ | 가상계좌 원장 |
| runtime/finance/policy_learning/ | 정책·학습 작업·Replay·평가 |
| runtime/finance/all_backend_features/results/ | 원본 모듈 수동 실행 결과 |
| runtime/finance/moe/ | Expert 실행 상태·구성 작업 |
| runtime/rea/program_analysis/ | 분석 입력·도구·임시 자료 |
| runtime/rea/project_explorer/projects/ | 저장한 분석 프로젝트 |
| runtime/ai_agent/Hermes/ | 헤르메스 대화·세션·설정·MCP·스킬 |
| runtime/shared/engines/ | 여러 메뉴가 공유하는 실행기 |

별도 생성 파일이 없는 메뉴는 빈 런타임 폴더를 만들지 않습니다. 원본 모델과 모델별 JSON은 바탕화면 모델 폴더를 계속 사용합니다. 기존 런타임 이동은 development/scripts/runtime_layout.py가 담당하며 서버·감시기·작업 프로세스를 중지한 상태에서만 사용합니다. 같은 이름의 목적지가 있으면 덮어쓰지 않습니다. 원본 모델을 역직렬화하거나 변환하지 않습니다.
