# 설치 요구사항

- operations.txt: 플랫폼·금융·Expert의 기존 주 환경 요청 명세. finrl_trading.txt를 포함합니다.
- finrl_trading.txt: FinRL-X 연결에 필요한 요청 명세를 기존 버전 그대로 분리한 파일. 다른 기능도 공유할 수 있으므로 제거 목록이 아닙니다.
- operations.lock.txt: 기존 주 환경 전체 잠금 명세. 이번 파일 분리로 재설치·버전 변경·잠금 재생성을 하지 않았습니다.
- kiwoom.txt, kiwoom.lock.txt: .venv/kiwoom의 기존 별도 SDK 환경.
- verification.txt: 사용자가 실행하는 검사 의존성.

원본 FinRL-X는 backend/stockrl/finrl_trading/library/finrl_x/ Git 서브모듈입니다. Python 패키지를 새 가상환경에 복제하거나 공식 소스를 수정하지 않았습니다. 개입 범위는 backend/stockrl/finrl_trading/README.md를 읽습니다.
