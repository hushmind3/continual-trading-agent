# 시장·저장 데이터

| 항목 | 내용 |
| --- | --- |
| 담당 메뉴 | 시장·저장 데이터 |
| 주요 파일 | MarketScanner.tsx / CollectionPanel.tsx |
| 역할 | 저장 종목·가격·OHLCV·수집 입력 |
| 기존 API operation/조회 | collect; state의 data / connections / prices 조회 |

공통 시장 화면이며 FMP 수집과 DataStore는 백엔드 finrl_trading 보조 경로를 사용합니다.

모든 호출은 data/Operations.tsx와 단일 /api를 사용합니다. 부모 폴더 변경 시 import 경로와 shell/Shell.tsx의 메뉴 연결을 함께 갱신합니다.
