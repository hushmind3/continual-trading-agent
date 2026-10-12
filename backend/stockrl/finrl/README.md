# FinRL · 메인

알고리즘 기반은 설치된 FinRL DRLAgent와 SB3입니다. 기본 선택은 SAC이며 목록과 기본값은 설치 소스에서 읽습니다.

| 파일 | 역할·진입점 |
| --- | --- |
| framework.py | 공식 환경, training_environment, train, backtest, 정책 선택·체크포인트 경로 |
| operations.py | FinRL ACTIONS와 execute; stock_data/stock_train/stock_backtest, Yahoo, features, data_split, finrl_stats, 공식 CLI |

## 연결

- 정책 학습: web_api → job_worker → official_cli → framework.train.
- 공식 기능: 공통 framework_operations → operations.execute.
- 상태: stock_state → 단일 state 응답의 finrl 조회 항목.
- 운영 환경과 주식거래 환경의 계약을 구분합니다. 동일 알고리즘이라고 모델 호환으로 처리하지 않습니다.
- 기존 DataStore 가격은 finrl_trading.data.prices, 비중 평가 결과는 finrl_trading.backtest.evaluate_weights를 사용합니다.
- 프론트 대응 구역: FinRL · 메인.
