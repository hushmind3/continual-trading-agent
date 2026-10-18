# 앱 설치·실행·제거 백엔드

용도: 프로젝트 관리 소메뉴의 설치 트랜잭션과 앱 소유 파일·연결 수명주기를 담당합니다.

- `handlers.py` → `manager.py` → 전체 메뉴 매니저 → 단일 `/api`에 등록합니다.
- `installer.py`, `adapters.py`, `node_mcp.py`: 원본 진입점 탐지, 의존성 설치, 실행·UI 확인, 메뉴와 MCP 자동 연결. 모델 변환은 `allow_agent=true`로 명시한 설치·재시도에서만 실행합니다.
- `python_packages.py`: 공용 Python 실행기를 재사용하되 앱 의존성은 해당 소스의 `.platform-runtime/python`에 설치합니다. `app_worker.py`, `runtime.py`는 그 경로를 자식 실행기에만 전달합니다. native 모듈은 공용 의존성이 이미 충족돼야 하며 설치기가 공용 Python을 변경하지 않습니다.
- `lifecycle.py`: 앱 소유 모듈·소스·의존성·설정·기록·내보낸 파일과 MCP 연결을 함께 제거합니다. 분리는 파일을 보관하며 재연결 때 재설치하지 않습니다. 이전 버전에서 공용 Python에 설치한 패키지는 소유 기록이 없으므로 임의로 지우지 않습니다.
- `packages.py`, `package_import.py`: ZIP 내보내기/가져오기. 파일 해시·중복·경로·크기 검증 후 기존 설치 트랜잭션을 재사용합니다. 해시는 손상 검사용이며 게시자 서명은 아닙니다. 다운로드는 `runtime.register_host`의 동일 호스트 파일 경로입니다.
- `portable_runner.py`, `portable_web.py`: ZIP에 포함되는 표준 라이브러리 기반 독립 실행기. 플랫폼·Codex·사용자 모델이 없어도 정적/Vite/FastAPI/Python CLI/Node MCP 원본 실행을 준비합니다. 독립 실행한 앱은 플랫폼과 별개이므로 자체 로컬 웹 포트를 사용할 수 있습니다.
- `localization.py`: 준비된 유휴 모델만 번역에 사용합니다. 번역 때문에 모델을 불러오지 않습니다. 꺼진 모델·작업 중에는 원문을 표시합니다.

API: `projects/install`, `retry`, `settings`, `detach`, `reconnect`, `remove`, `export`, `import`, `agent/connect`, `agent/start`. 데이터와 검사 자료는 `runtime/projects/manage/` 소속입니다. 내보내기는 앱별 `projects/<ID>/exports/`, 가져오기 임시는 `imports/`이며 설치 성공·실패·취소 뒤 정리합니다.

검사 명령·현재 한계·실제 결과는 [상위 안내](../README.md)를 따릅니다. 외부 native 모듈과 임의 데스크톱 앱 변환은 기존 외부 앱 ZIP 대상이 아닙니다. 기본 금융·REA·Hermes는 별도 standalone-module 소스 배포 형식으로 지원합니다.

- builtin_packages.py: finance/rea/hermes만 받아 선택 모듈·공통 호스트/UI 소스 복사본·의존성 명세·전용 설치/실행 진입점을 ZIP에 넣습니다. 다른 모듈·실제 가상환경·데이터·비밀 설정은 제외합니다. 기존 projects/export와 안전한 project-packages 다운로드 경로를 사용합니다.
- standalone_runner.py: 원래 프로젝트 경로를 찾지 않고 추출한 폴더를 ROOT로 사용합니다. 상속된 PLATFORM_ROOT/PLATFORM_MODULES_DIR/PYTHONPATH/HERMES_HOME을 정리하며 setup/check/run을 제공합니다. 설치는 기존 install_windows.py·module_sources.py를 복사해 재사용합니다. Hermes 모델 실행기는 공개 URL·해시를 내보내 setup에서 검증·설치합니다. Windows 전용 설치이며 모델/키/기존 데이터는 별도 준비합니다.
- development/tests/test_builtin_packages.py: 다른 모듈/비밀/환경 제외, 경로·무결성·실행 환경, 실행기 SHA-256과 압축 경계 검사. 실제 단독 실행 검사는 development/scripts/verify_standalone_modules.py이며 자세한 조건은 상위 README를 따릅니다.

현재 분리 경로: projects/detach는 detachment.start의 비동기 작업으로 실행합니다. 현재 패키지·독립 실행 진입점·필요한 UI를 준비한 뒤 원래 프로그램과 해당 모듈 data 항목을 이동합니다. builtin_record는 기본 모듈을 같은 작업 목록에 등록하고 reconnect_builtin은 원래 위치로 되돌립니다. 롤백 실패 시 파일을 보존하고 오류를 표시합니다.

cleanup.py는 이전 ZIP/가져오기 잔재를 휴지통으로 이동합니다. projects/cleanup·projects/folder/open은 각각 정리와 실제 앱 폴더 열기입니다. requirements.py는 문서 저장소를 실행 앱과 구분합니다. 검증 파일은 development/tests/test_project_detachment.py 및 development/scripts/verify_project_detachment.cjs입니다. Node MCP 연결은 이전 .venv/hermes 대신 modules/hermes/.venv를 사용합니다.

Windows 설치기: powershell_app.py·powershell_metadata.ps1은 원본 PS AST만 읽어 옵션을 탐지합니다. adapters.py의 powershell 유형은 runtime.verify에서 문법만 확인하며 entry_executed로 표시하지 않습니다. 원본 실행은 projects/setup 사용자 요청에서만 별도 프로세스로 시작하며 runtime.ACTIVE로 서버 적용·제거를 보호합니다. setup/folder는 사용자 클릭 시에만 Windows 폴더 선택 창을 엽니다. setup/status는 JSON과 최근 로그만 읽고 매번 PowerShell을 띄우지 않습니다. 임시 다운로드는 해당 설치 버전의 setup-cache에 격리합니다. 원본 설치기가 지정 대상 폴더에 만든 파일은 저장소 제거로 자동 복원/제거되는 대상이 아닙니다. 회귀 명령: .venv/Scripts/python.exe -X utf8 -B -m unittest development.tests.test_project_windows_installer -q.

store.project_folder/install_folder가 프로젝트 관리 앱별 부모/application 경로를 계산합니다. 기존 버전/설정/전용 패키지 경로를 이동하지 않고 동일 부모를 유지합니다. powershell_app.describe는 설치 대상 매개변수만 managed로 표시하고 start가 앱 내부 경로를 강제 사용해 외부 입력 경로로 설치되지 않게 합니다. 필수 기존 프로그램 입력은 자동 설치 경로로 오분류하지 않습니다.
