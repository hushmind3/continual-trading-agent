# Execution and setup

- start_server.py: 기존 소유 서버에 소스를 적용하고 단일 API를 실행합니다.
- install_windows.py: 기존 주 환경·키움·REA 설치 진입점입니다.
- requirements/: 기존 의존성과 고정 버전 명세. 파일 내용·버전은 변경하지 않았습니다.

루트 `서버켜기.cmd`·`설치.cmd`에서 호출합니다. `.venv/`·`.venv-kiwoom/` 경로는 유지합니다. 외부 소스는 vendor/FinRL-X/입니다.

사용자 검사: 루트에서 `.venv\Scripts\python.exe -m unittest discover -s tests`, frontend 폴더에서 `npm run typecheck`, `npm run test:api`, `npm run test:browser`. 요청 없는 자동 검사·백그라운드 검사는 실행하지 않습니다.
