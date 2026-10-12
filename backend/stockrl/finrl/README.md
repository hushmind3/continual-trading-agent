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

## 메뉴 연결 파일

finrl_menu_manager.py가 이 구역의 작은 메뉴만 import합니다.

| 화면 | 연결 파일 | 프론트 담당 파일 |
| --- | --- | --- |
| 정책 학습 | policy_learning_menu.py | pages/training/TrainingWorkspace.tsx |
| 정책 평가 · 백테스트 | policy_evaluation_menu.py | pages/portfolio/PortfolioWorkspace.tsx |
| 주식거래 데이터 준비 | stock_data_menu.py | pages/finrl/FinrlWorkspace.tsx |
| 주식거래 알고리즘 학습 | stock_training_menu.py | pages/finrl/FinrlWorkspace.tsx |
| 주식거래 백테스트 | stock_backtest_menu.py | pages/finrl/FinrlWorkspace.tsx |
| FinRL 모듈 · 도구 | finrl_tools_menu.py | pages/frameworks/FrameworkWorkspace.tsx |
