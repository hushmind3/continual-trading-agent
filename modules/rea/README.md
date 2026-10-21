# REA 역공학 모듈

용도: 기존 REA 대메뉴의 소스·Python/Node 패키지·설정을 자체 소유합니다. GitHub에서 별도로 설치한 morluto/rea 앱과 구분합니다.

- `backend/`: `rea` 패키지·분석/탐색·자체 경로/JSON 처리·worker.py. 금융 `stockrl`을 import하지 않습니다.
- `frontend/`: REA 화면·소메뉴 매니저. 호스트의 React/Vite/Tailwind·UI 등록 규격을 사용합니다.
- `.venv/`, `requirements.txt`: Python 실행 환경·의존성.
- `node_modules/`, `package.json`, `package-lock.json`: 원본 REA 6.4.0과 Node MCP 클라이언트의 독립 설치 위치. 루트 node_modules를 참조하지 않습니다.
- `configs/rea.json`: 도구 경로 설정, Git 제외. 연결 상태의 분석 작업과 저장 결과는 `runtime/rea/`에 저장하며 로컬 분리 시 해당 폴더도 함께 옮깁니다.

연결: 소메뉴 → rea_menu_manager → worker.py → backend/register.py → 전체 메뉴 → 단일 `/api`. Python 작업은 자체 가상환경에서 수행하고 원본 Node MCP는 자체 패키지로 실행합니다. 별도 HTTP 서버는 없습니다. 원본 Node 코드를 Python으로 변환하지 않습니다.

설치: Mac 루트 `설치.command` / Windows `설치.cmd`, 또는 해당 폴더에서 `npm ci --workspaces=false`. Python은 `requirements.txt`로 `.venv`에 설치합니다. 기존 환경을 재사용하는 분리는 루트 `.venv/Scripts/python.exe -B development/scripts/isolate_module_environment.py rea`입니다. old `backend/rea` 경로는 import 호환 연결만 남습니다.

현재 확인과 미확인은 [모듈 안내](../README.md)에 구분합니다. 원본 분석 모델이나 로그인 사이트·네이티브 앱 전체 실행 검증은 이번 환경 분리의 확인 범위가 아닙니다.

로컬 분리: GitHub → 프로젝트 관리 → 설치된 프로젝트에서 **분리**를 누르면 실제 프로그램·전용 환경·소유 데이터/설정을 독립 폴더로 옮깁니다. `실행.command`(Mac) / `실행.cmd`(Windows)로 실행하고 다시 연결하면 같은 파일을 복원합니다. 원본 모델은 사용자 지정 위치에 유지합니다.

전달용 소스 ZIP: 설치 정보 → 개발자 상세에서 선택적으로 저장합니다. 압축을 푼 뒤 `python run.py setup`, `check`, `run --port 8080`으로 설치·검사·실행합니다. 필요한 공통 API/UI는 ZIP 안의 복사본을 사용합니다. 기존 데이터·비밀 설정·모델은 자동 포함하지 않습니다. 형식·실제 확인 범위는 [프로젝트 관리](../projects/README.md)를 따릅니다.
