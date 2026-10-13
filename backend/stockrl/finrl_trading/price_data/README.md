# 저장 가격 조회

- 핵심 파일·진입점: operations.py의 prices(currency, symbols), price_store, price_processor, collection_status; market_storage.py의 AppendOnlyMarketCSV.
- 사용처: 금융 policy_learning, trading/operation_control 및 platform의 공식 함수 실행·Expert 추론.
- 필수 의존성: 상위 finrlx → 공식 data.data_store, pandas, SQLite, stockrl.ROOT.
- 보호 대상: 기존 data/·runtime/ 가격 자료를 그대로 사용합니다.
- 상태: import 경로 재배치 완료. 실제 학습·추론·가격 조회 검사는 미실행입니다.

공식 data.data_store·data.data_processor·data.data_fetcher 호출을 이 폴더에 모았습니다. live_feed는 market_storage를 import하고 연결·설정은 collection_status를 호출합니다. Expert 입력은 price_store와 prices를 사용합니다. 다른 코드에 같은 저장 구현을 복제하지 않습니다.
분리 회귀 검사는 사용자가 PYTHONPATH=backend 설정 후 development/tests/test_state_integrity.py를 실행합니다. 에이전트는 실행하지 않았습니다. 전체 사용처는 ../README.md에 있습니다.
