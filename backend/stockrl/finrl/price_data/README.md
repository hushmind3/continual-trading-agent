# 저장 가격 조회

- 핵심 파일·진입점: operations.py의 prices(currency, symbols), price_store, collection_status; storage.py의 PriceStore·clean_price_data; market_storage.py의 AppendOnlyMarketCSV.
- 사용처: 금융 policy_learning, trading/operation_control 및 platform의 공식 함수 실행·Expert 추론.
- 필수 의존성: pandas, Python 표준 SQLite, stockrl.ROOT. FinRL-X import는 없습니다.
- 가격 DB: data/market_prices.sqlite3. 사용자 지시에 따라 기존 DB를 복사하지 않고 새 저장소를 사용합니다. 원본 실시간 CSV·봉 데이터는 runtime/에 있습니다.
- 상태: 가격 정리·중복 제거·저장·조회·업데이트·주기 분리 회귀 검사가 통과했습니다. 실제 시세 수신·학습은 별도 단계입니다.

기존 가격 정리 규칙을 금융 백엔드에서 처리합니다. live_feed는 market_storage를 import하고 연결·설정은 collection_status를 호출합니다. Expert 입력은 price_store와 prices를 사용합니다. 다른 코드에 같은 저장 구현을 복제하지 않습니다.
회귀 검사: PYTHONPATH=backend 설정 후 python -B -m unittest discover -s development/tests. 이번 작업에서 실제 실행했습니다.
