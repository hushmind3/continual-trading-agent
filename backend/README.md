# Backend platform

| 위치 | 역할 |
| --- | --- |
| [stockrl/](stockrl/README.md) | 금융 대메뉴: 현재 금융 화면 7개 |
| [rea/](rea/README.md) | 독립 REA 프로젝트: program_analysis/, project_explorer/ |
| [menu_registry.py](menu_registry.py) | 금융·REA 두 대메뉴를 등록·취합하는 총괄 |
| [web_api.py](web_api.py) | 단일 /api 진입점; 총괄만 통해 기능 등록 |
| api_context.py, api_transport.py | 공유 HTTP 객체·요청 전달·React 제공 |
| rea/project_explorer/saved_projects/ | 저장된 원본·추론 분석 결과; 실행 기능 등록 대상이 아니며 Git 제외 |

하위 기능 → 소메뉴 매니저 → 대메뉴 → 전체 메뉴 매니저 → API.
각 프로젝트와 작은 메뉴 README를 먼저 읽습니다. 새 기능은 자기 프로젝트의 매니저로 등록합니다. 구조 이름은 영문 ASCII입니다.

Python 설치 메타데이터는 .venv/Lib/site-packages/continual_trading_agent-0.1.0.dist-info/에 있습니다. backend/의 같은 버전 egg-info는 setuptools 빌드 잔여물이어서 휴지통으로 이동했습니다. __pycache__/는 Python이 생성하는 캐시이며 대메뉴가 아닙니다.
