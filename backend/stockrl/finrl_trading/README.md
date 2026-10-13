# 공통 가격·공급원 연결

FinRL-Trading 큰 메뉴와 보조 실행 5개는 제거했습니다. 전용 메뉴 관리자·화면 어댑터는 휴지통으로 이동했습니다.

| 파일 | 현재 사용처 |
| --- | --- |
| __init__.py | 고정된 공식 FinRL-X 원본의 지연 import |
| data.py | 중앙 FinRL 학습·운영에서 사용하는 DataStore 가격 조회 |
| operations.py | 가격 수집·원본 함수 호출·연결 설정의 provider_environment/provider_status/save_provider |

ACTIONS와 execute 및 Adaptive Rotation 데이터 준비·단일 실행·전체 백테스트·거래일·설정 검사 어댑터는 없습니다. 공통 인증·가격 조회의 호출처가 남아 있어 해당 코드와 공식 FinRL-X 원본을 유지합니다. 공식 소스·모델·가격·계좌·인증은 변경하지 않았습니다.
