# FinRL-Trading · 보조

공식 원본은 프로젝트 최상위 FinRL-X/입니다. 이 폴더는 필요한 보조 기능의 연결 코드이며 기본 학습기를 소유하지 않습니다.

| 파일 | 역할·진입점 |
| --- | --- |
| __init__.py | finrlx: 필요한 원본 모듈을 지연 import |
| data.py | prices: 기존 DataStore 가격 조회·일봉 구분 |
| backtest.py | evaluate_weights: 기존 StrategyResult·BacktestEngine 호출 |
| operations.py | 보조 ACTIONS·execute; 추가 수집·처리·전략·성과·공급원 보안 설정 |

## 연결

- 공통 API 중계는 ACTIONS 소유 폴더에 따라 execute를 호출합니다.
- 공급원: provider_environment, provider_status, save_provider.
- 설정·가격·비중 평가의 기존 계약과 기본값을 유지합니다.
- A2C·DDPG·PPO·TD3·SAC 알고리즘 선택·학습은 finrl/에서 담당합니다.
- 프론트 대응 구역: FinRL-Trading · 보조. 인증 설정은 공통 연결·설정 화면에서도 접근합니다.

## 메뉴 연결 파일

finrl_trading_menu_manager.py가 이 구역의 작은 메뉴만 import합니다.

| 화면 | 연결 파일 | 프론트 담당 파일 |
| --- | --- | --- |
| 보조 데이터 · 전략 · 도구 | finrl_trading_tools_menu.py | pages/frameworks/FrameworkWorkspace.tsx |
