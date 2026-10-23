# 금융 백엔드

용도: 금융 모듈의 실제 `stockrl` 구현입니다. `trading/`, `finrl/`, `extensions/`, `management/`의 소메뉴 매니저를 finance_menu_manager.py가 취합하고 worker.py가 전용 환경에서 실행합니다.

`api_context.py`, `catalog.py`, `transport.py`, `state_io.py`는 금융이 소유합니다. REA·Hermes에서 이 파일들을 import하지 않습니다. register.py는 호스트의 등록/IPC 인터페이스만 사용하며 업무 패키지를 호스트에 import하지 않습니다.

경로·설정·패키지·확인 방법은 [금융 모듈](../README.md)을 따릅니다. 설정은 `../configs/`, 실제 Python 패키지는 `../.venv/`입니다. 외부 모델과 기존 원장은 이동하지 않았습니다.
