# FinRL-Trading 공통 백엔드

금융 대메뉴가 사용하는 공식 소스와 연결 모듈입니다. 독립 대메뉴·신규 화면은 등록하지 않습니다.

| 폴더 | 역할·진입점 |
| --- | --- |
| price_data/ | operations.prices: 중앙 학습·운영의 저장 가격 조회 |
| provider_settings/ | operations: 공통 공급원 인증 설정 조회·저장 |
| library/ | 수정하지 않은 공식 FinRL-X 서브모듈 |

__init__.py의 finrlx(name)가 library/finrl_x/에서 공식 모듈을 지연 import합니다. 각 소비 메뉴의 구현이 연결 모듈을 호출하며, 메뉴 등록·단일 API 계층은 유지합니다. React 화면은 frontend/src/pages/finance/에 있습니다.
폴더 이동 완료. 모델·가격·계좌·인증과 공식 알고리즘은 변경하지 않았으며 이번 작업의 실행 검사는 미실행입니다.
