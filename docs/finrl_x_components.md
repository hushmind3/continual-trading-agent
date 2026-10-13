# FinRL-X component inventory

현재 원본은 backend/stockrl/finrl_trading/library/finrl_x/src/ 아래 기능 영역별 폴더로 나뉘어 있습니다. 원본 import·설정·알고리즘·가격 데이터는 변경하지 않았습니다.

## 현재 플랫폼이 유지하는 직접 의존

- stockrl.finrl_trading.price_data.operations.prices → src.data.data_store.DataStore: 저장 가격 조회.
- stockrl.market_storage.AppendOnlyMarketCSV → DataStore + DataProcessor: 완료 바를 저장소에 추가·처리.
- stockrl.finrl_trading.provider_settings.operations → src.config.settings: 공급원 설정·공통 인증 설정 연결.
- 일반 공식 함수 실행은 나머지 원본 공개 함수의 호출 가능 경로이며, 중앙 운영에서 실행됐다는 뜻은 아닙니다.

## 백엔드 이동 시 함께 확인할 필수 내부 모듈

- config.settings →
- data.data_processor →
- data.data_store → config.settings, data.trading_calendar
- data.trading_calendar →

## 영역별 실제 폴더

- src/data/: 데이터 수집·저장·처리; 9개 해석 가능 Python 파일.
- src/config/: 공통 설정; 2개 해석 가능 Python 파일.
- src/utils/: 공통 로깅·보조 함수; 1개 해석 가능 Python 파일.
- src/strategies/: 전략; 27개 해석 가능 Python 파일.
- src/backtest/: 백테스트; 2개 해석 가능 Python 파일.
- src/trading/: 브로커·주문·성과; 3개 해석 가능 Python 파일.
- src/tools/: 공식 도구; 1개 해석 가능 Python 파일.
- src/web/: 공식 Streamlit 화면; 3개 해석 가능 Python 파일.

## 소스 해석 미확인

- trading/alpaca_manager.py: UnicodeDecodeError

## 적용 결과

- 공식 저장소를 vendor/FinRL-X에서 금융 백엔드의 library/finrl_x로 이동했습니다. 기존 8개 원본 영역 폴더·공식 소스·서브모듈 커밋은 유지했습니다.
- 가격 조회 연결은 price_data/operations.py, 공급원 설정 연결은 provider_settings/operations.py로 나누고 각 폴더에 README를 배치했습니다.
- 소비 모듈 import, 설치·서버 적용 경로, 공식 함수 카탈로그 경로를 함께 수정했습니다. 공식 소스를 금융 자체 모듈로 중복 집계하거나 Python 패키지로 중복 설치하지 않습니다.
- React 화면은 기존 frontend/src/pages/finance/에 유지합니다. 공식 Streamlit 코드는 원본으로만 보존하며 신규 UI·메뉴를 만들지 않았습니다.
- 실행·학습·백테스트·타입·브라우저·진단 검사는 미실행입니다. 사용자가 기존 검사 스크립트를 실행합니다.
