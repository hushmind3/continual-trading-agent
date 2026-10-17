# 금융 모듈

용도: 금융 대메뉴의 소스·패키지·설정·운영 데이터 소유와 플랫폼 연결을 설명합니다.

- `backend/`: 실제 `stockrl` 소스. 소메뉴 → finance_menu_manager → worker.py로 취합합니다.
- `frontend/`: 금융 화면과 소메뉴 매니저. 플랫폼의 React/Vite/Tailwind 렌더러·공통 UI 인터페이스에 등록합니다.
- `dependencies/operations.txt`, `operations.lock.txt`: 금융 전용 패키지 명세·잠금. `dependencies/kiwoom*`: SDK 전용 명세.
- `.venv/`: 금융 Python·실제 설치 패키지. `.venv/kiwoom/`: SDK 전용 환경. 기본 호스트 환경을 변경하지 않습니다.
- `configs/instruments.json`, `configs/local/operations.json`: 금융 전용 설정. local은 Git 제외입니다.
- 데이터는 기존 `runtime/finance/`, `data/market_prices.sqlite3`에 유지하며 module.json에 소유를 선언합니다. 모델 원본은 사용자가 지정한 모델 폴더에 유지합니다.

`backend/register.py`는 호스트 연결 어댑터입니다. 단일 `/api`가 `module-jsonl-v1`으로 금융 전용 프로세스에 전달합니다. 별도 HTTP 서버는 띄우지 않습니다. 금융 소스·FinRL·Torch를 플랫폼 Python에 import하지 않습니다. `backend/stockrl/`의 이전 경로는 호환 이름 연결만 남았으며 실행 구현은 이 모듈에 있습니다.

설치: 루트 `설치.cmd`. 이미 설치된 환경의 패키지를 다운로드 없이 분리하려면 `.venv/Scripts/python.exe -B development/scripts/isolate_module_environment.py finance` 및 `kiwoom`. 해당 명령은 버전을 바꾸지 않고 선택된 배포본과 의존성을 전용 환경에 복사합니다. `.venv`와 패키지 산출물은 Git 제외이며 소스·명세만 배포합니다.

현재 확인/한계는 [모듈 안내](../README.md)의 환경 분리 항목을 봅니다. 플랫폼 UI와 등록·IPC 규격은 연결 인터페이스이며, 플랫폼 없는 완성 앱이나 다른 PC용 컴파일 배포를 완료했다는 뜻이 아닙니다.
