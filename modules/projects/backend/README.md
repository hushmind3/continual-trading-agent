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

검사 명령·현재 한계·실제 결과는 [상위 안내](../README.md)를 따릅니다. native/플랫폼 포함 모듈의 완전 독립 배포, 임의 데스크톱 앱 변환은 이 ZIP 기능으로 완료된 것이 아닙니다.
