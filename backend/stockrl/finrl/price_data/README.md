# 저장 가격 조회

- 핵심 파일·진입점: operations.py의 prices(currency, symbols), price_store, collection_status; storage.py의 PriceStore·clean_price_data; market_storage.py의 AppendOnlyMarketCSV.
- 사용처: 금융 policy_learning, trading/operation_control 및 platform의 공식 함수 실행·Expert 추론.
- 필수 의존성: pandas, Python 표준 SQLite, stockrl.ROOT. FinRL-X import는 없습니다.
- 가격 DB: data/market_prices.sqlite3. 사용자 지시에 따라 기존 DB를 복사하지 않고 새 저장소를 사용합니다. 원본 실시간 CSV·봉 데이터는 runtime/에 있습니다.
- 상태: 가격 정리·중복 제거·저장·조회·업데이트·주기 분리 회귀 검사가 통과했습니다. 실제 시세 수신·학습은 별도 단계입니다.

기존 가격 정리 규칙을 금융 백엔드에서 처리합니다. live_feed는 market_storage를 import하고 연결·설정은 collection_status를 호출합니다. Expert 입력은 price_store와 prices를 사용합니다. 다른 코드에 같은 저장 구현을 복제하지 않습니다.
회귀 검사: PowerShell에서 `$env:PYTHONPATH='backend;development/tests'` 설정 후 `.\.venv\Scripts\python.exe -B -m unittest test_kiwoom_history`를 사용합니다. 최신 출처·주기·시각 저장 변경 이후에는 실행하지 않았습니다.

키움 원본 가격: collect_kiwoom_prices는 기존 격리 SDK의 ka10081로 등록된 국내 종목의 최근 완료 일봉을 조회합니다. normalize_kiwoom_daily가 날짜·가격·중복을 검증한 뒤 같은 PriceStore에 저장합니다. 정책 학습 화면의 키움 가격 수집은 start_kiwoom_collection을 호출하고 price/history 조회로 실제 완료·일부 실패를 표시합니다. 중앙 API 파일은 수정하지 않습니다. 미국 가격·분봉·추가 연속조회는 이 일봉 수집 작업의 범위에 포함되지 않습니다.

PriceStore는 종목·시각·출처·주기를 함께 구분합니다. 일봉은 거래일을 유지하고, 분봉·장중 시각은 UTC와 나노초를 보존합니다. 같은 출처·주기의 같은 봉만 갱신하며 다른 출처·주기를 덮어쓰지 않습니다. 날짜만 지정한 조회 종료일은 해당 날짜의 장중 봉까지 포함합니다. 과거 날짜로 축약돼 덮어쓰인 봉은 이 변경으로 복원되지 않습니다.

기존 UNIQUE(ticker,date) 저장소는 다음 초기화 때 단일 트랜잭션으로 새 키에 이관합니다. 기존 ID·행·시각·출처·주기·생성 기록 및 사용자 인덱스·트리거를 보존합니다. 종목·시각만 제한하는 구형 유일성 인덱스는 새 키로 대체합니다. 알 수 없는 열이나 이관 오류가 있으면 전체 취소합니다. 이번 작업에서 실제 사용자 DB의 이관을 실행하지 않았습니다. live CSV·timeframes.sqlite3의 수신 경로와 실시간 학습 연결은 별도이며, 이 저장 수정만으로 연결 완료를 주장하지 않습니다.
