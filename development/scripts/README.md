# Execution and setup

- start_server.py: 기존 소유 서버에 소스를 적용하고 단일 API를 실행합니다.
- install_windows.py: 기존 주 환경·키움·REA 설치 진입점입니다.
- requirements/: 기존 의존성과 고정 버전 명세. 파일 내용·버전은 변경하지 않았습니다.

루트 `서버켜기.cmd`·`설치.cmd`에서 호출합니다. `.venv/`·`.venv/kiwoom/` 경로는 유지합니다. FinRL-X 외부 원본과 설치 연결은 제거했습니다. 금융 데이터 코드는 backend/stockrl/finrl/price_data/와 provider_settings/에 있습니다.

사용자 검사: 루트에서 `.venv\Scripts\python.exe -m unittest discover -s development/tests`, frontend 폴더에서 `npm run typecheck`, `npm run test:api`, `npm run test:browser`. 요청 없는 자동 검사·백그라운드 검사는 실행하지 않습니다.

npm은 루트 workspace 설치를 사용합니다. REA install()은 루트 npm ci로 프론트와 REA의 고정 버전을 함께 설치합니다. 검사 명령은 루트 npm run typecheck/test:api/test:browser로도 실행할 수 있습니다.

모듈 참조 조사: .venv\Scripts\python.exe -B development/scripts\audit_module_usage.py. AST·import 경로만 읽어 운영 참조·검사 전용·참조 없음 후보를 출력합니다. 플랫폼 코드 import·함수 실행·삭제는 수행하지 않습니다.

서버켜기.cmd는 서버·현재 프론트만 적용하고 화면을 엽니다. 전체 시스템 시작(system/start), 시세·추론·학습·매매 및 자동 진단은 호출하지 않습니다. Git/Node는 이미 설치된 실행 파일을 사용하며 추가 설치하지 않습니다.
