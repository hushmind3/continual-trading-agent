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

현재 확인/한계는 [모듈 안내](../README.md)의 환경 분리 항목을 봅니다. 플랫폼 UI와 등록·IPC 규격은 연결 인터페이스이며, 프로젝트 관리의 독립 실행 소스는 필요한 공통 코드 복사본과 설치/실행 진입점을 포함합니다. 다른 PC 신규 설치·시세/학습/주문 전체와 컴파일 배포를 확인한 뜻은 아닙니다.

로컬 분리: GitHub → 프로젝트 관리 → 설치된 프로젝트에서 **분리**를 누르면 실제 프로그램·전용 환경·소유 데이터/설정을 독립 폴더로 옮깁니다. `실행.cmd`로 실행하고 다시 연결하면 같은 파일을 복원합니다. 원본 모델은 사용자 지정 위치에 유지합니다.

전달용 소스 ZIP: 설치 정보 → 개발자 상세에서 선택적으로 저장합니다. 압축을 푼 뒤 `python run.py setup`, `check`, `run --port 8080`으로 설치·검사·실행합니다. 필요한 공통 API/UI는 ZIP 안의 복사본을 사용합니다. 기존 데이터·비밀 설정·모델은 자동 포함하지 않습니다. 형식·실제 확인 범위는 [프로젝트 관리](../projects/README.md)를 따릅니다.

macOS 실행: `dependencies/operations-macos.txt`에 고정한 Python 3.11 전용 환경을 `modules/finance/.venv/`에 준비합니다. `설치.command`도 같은 환경을 설치합니다. 금융 모듈은 기존 JSON-line 실행기와 단일 `/api`로 연결합니다. Windows CUDA·키움 전용 의존성은 Mac 설치 대상에서 제외합니다. 금융 원본 소스·가격/학습/거래 데이터·모델 파일은 보존하며 Mac에서 학습·주문이 완료됐다고 표시하지 않습니다. 공통 호스트는 해당 전용 환경과 분리돼 실행합니다. Mac 공통 실행 경로는 ../../backend/README.md를 따릅니다.

2026-10-23 복구 진행: Mac 설치에서 금융을 통째로 제외하던 경로를 수정했습니다. 기존 worker의 실제 등록 응답과 8766의 `operations`·`resources`·`capabilities` 정상 반환, 모듈 오류 0개, 운영 제어 화면 표시를 확인했습니다. 시세·학습·주문은 실행하지 않았습니다.
