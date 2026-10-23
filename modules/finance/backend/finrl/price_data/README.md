# 저장 가격 조회

Expert 원본 미국 입력: collect_kiwoom_prices(symbols,currency='USD')는 기존 키움 격리 SDK의 usa10098 거래소 조회·usa06012 일 차트를 사용합니다. 등록 Expert의 원본 universe에 있는 종목만 조회하여 같은 PriceStore에 source=kiwoom/timeframe=1d로 저장합니다. 자동 시작은 누락 종목 이력을 수집합니다. 실제 CRWD·META·T 각 100개 최근 완료 일봉 수집·저장 완료. 주문 API·개별 Expert 추론 검사는 실행하지 않았습니다.

- 핵심 파일·진입점: operations.py의 prices(currency, symbols), price_store, collection_status; storage.py의 PriceStore·clean_price_data; market_storage.py의 AppendOnlyMarketCSV.
- 사용처: 금융 policy_learning, trading/operation_control 및 platform의 공식 함수 실행·Expert 추론.
- 필수 의존성: pandas, Python 표준 SQLite, stockrl.ROOT. FinRL-X import는 없습니다.
- 가격 DB: data/market_prices.sqlite3. 사용자 지시에 따라 기존 DB를 복사하지 않고 새 저장소를 사용합니다. 원본 실시간 CSV·봉 데이터는 runtime/에 있습니다.
- 상태: 가격 정리·중복 제거·저장·조회·업데이트·주기 분리 회귀 검사가 통과했습니다. 실제 시세 수신·학습은 별도 단계입니다.

기존 가격 정리 규칙을 금융 백엔드에서 처리합니다. live_feed는 market_storage를 import하고 연결·설정은 collection_status를 호출합니다. Expert 입력은 price_store와 prices를 사용합니다. 다른 코드에 같은 저장 구현을 복제하지 않습니다.
회귀 검사: PowerShell에서 `$env:PYTHONPATH='backend;development/tests'` 설정 후 `.\.venv\Scripts\python.exe -B -m unittest test_kiwoom_history`를 사용합니다. 이번 변경 묶음에서 전체 102개 검사에 포함해 저장 이관·출처·주기·시각 회귀 검사를 통과했습니다.

키움 원본 가격: collect_kiwoom_prices는 기존 격리 SDK의 ka10081로 등록된 국내 종목의 최근 완료 일봉을 조회합니다. normalize_kiwoom_daily가 날짜·가격·중복을 검증한 뒤 같은 PriceStore에 저장합니다. 정책 학습 화면의 키움 가격 수집은 start_kiwoom_collection을 호출하고 price/history 조회로 실제 완료·일부 실패를 표시합니다. 중앙 API 파일은 수정하지 않습니다. 미국 가격·분봉·추가 연속조회는 이 일봉 수집 작업의 범위에 포함되지 않습니다.

PriceStore는 종목·시각·출처·주기를 함께 구분합니다. 일봉은 거래일을 유지하고, 분봉·장중 시각은 UTC와 나노초를 보존합니다. 같은 출처·주기의 같은 봉만 갱신하며 다른 출처·주기를 덮어쓰지 않습니다. 날짜만 지정한 조회 종료일은 해당 날짜의 장중 봉까지 포함합니다. 과거 날짜로 축약돼 덮어쓰인 봉은 이 변경으로 복원되지 않습니다.

기존 UNIQUE(ticker,date) 저장소는 다음 초기화 때 단일 트랜잭션으로 새 키에 이관합니다. 기존 ID·행·시각·출처·주기·생성 기록 및 사용자 인덱스·트리거를 보존합니다. 종목·시각만 제한하는 구형 유일성 인덱스는 새 키로 대체합니다. 알 수 없는 열이나 이관 오류가 있으면 전체 취소합니다. 이번 작업에서 실제 사용자 DB의 이관을 실행하지 않았습니다.

실시간 연결: AppendOnlyMarketCSV.append는 새 완료 봉을 먼저 출처·주기와 함께 PriceStore에 저장하고, 저장 개수가 일치해야 CSV와 수신 확인 목록에 반영합니다. 키움 완료 봉은 source=kiwoom·timeframe=1m이며 Yahoo는 요청 주기를 기록합니다. 기존 CSV는 헤더를 유지해 추가 행 형식을 깨뜨리지 않습니다. 과거 CSV에만 있는 봉은 자동 재수집·복원하지 않습니다.

prices(currency,symbols,timeframe='1d')에서 1m을 명시하면 선택 공급원의 완료 분봉만 읽습니다. 기본 일봉 조회는 명시적 분봉을 제외합니다. 정책 학습·운영 판단·지속학습은 저장 정책의 주기를 따릅니다. 서버 적용·브라우저 주기 전달·실제 일봉 이어 학습은 확인했습니다. 새로운 실시간 분봉 수신부터 학습까지의 실행은 아직 확인하지 않았습니다.
