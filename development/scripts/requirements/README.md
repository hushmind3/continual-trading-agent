# 설치 요구사항

- operations.txt: 플랫폼·금융·Expert의 주 환경 요청 명세. FinRL-X 명세를 포함하지 않습니다.
- operations.lock.txt: 주 환경 잠금 명세. Streamlit·Altair·Pydeck 항목을 제거했습니다. 다른 패키지 버전은 변경하지 않았습니다.
- kiwoom.txt, kiwoom.lock.txt: .venv/kiwoom의 기존 별도 SDK 환경.
- verification.txt: 사용자가 실행하는 검사 의존성.

FinRL-X 원본·서브모듈 등록·설치 단계와 Streamlit 설치 요청을 제거했습니다. 기존 환경의 Streamlit·Altair·Pydeck도 의존성을 확인한 뒤 프로젝트 휴지통으로 이동했습니다. FinRL/SB3 및 Expert가 공유하는 패키지는 일괄 삭제하지 않았습니다. 최신 결과는 development/docs/finrl_x_removal.md를 읽습니다.
