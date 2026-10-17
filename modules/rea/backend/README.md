# REA 백엔드

용도: 프로그램 분석·프로젝트 탐색의 실제 소스를 보관합니다. 각 소메뉴 README와 rea_menu_manager.py → worker.py를 따라 수정합니다.

`__init__.py`, `state_io.py`, `transport.py`는 REA 자체 경로/JSON 처리이며 금융 의존성이 아닙니다. Python은 `../.venv`, Node 패키지는 `../node_modules`, 설정은 `../configs/rea.json`을 사용합니다. register.py만 호스트와 연결하며 추가 HTTP 서버를 열지 않습니다.

설치·실행·현재 확인은 [REA 모듈](../README.md)을 봅니다. 저장 프로젝트는 기존 `runtime/rea/project_explorer/projects`에 유지합니다.
