# 환경별 설치 요구사항

용도: 호스트 및 기존 설치 명령의 호환 진입점을 관리합니다.

- platform.txt: `.venv/platform`의 최소 API/실행 관리 패키지.
- operations*.txt, kiwoom*.txt: `modules/finance/dependencies/`로 연결하는 호환 파일. 실제 명세·잠금은 금융 소유입니다.
- verification.txt: 개발 검사용 패키지이며 운영 모듈에 자동 설치하지 않습니다.
- REA: modules/rea/requirements.txt 및 package*.json. Hermes: modules/hermes/backend/engine/requirements*.txt와 browser/package*.json.

설치 위치와 확인 범위는 [모듈 안내](../../../modules/README.md)를 따릅니다.
