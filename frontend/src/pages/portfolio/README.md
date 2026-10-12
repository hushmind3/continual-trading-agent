# FinRL 정책 평가·백테스트

| 항목 | 내용 |
| --- | --- |
| 담당 메뉴 | FinRL 정책 평가·백테스트 |
| 주요 파일 | PortfolioWorkspace.tsx / ResultTable.tsx |
| 역할 | 평가 대상·검사·실행·지표·가치 추이·비중/거래 CSV |
| 기존 API operation/조회 | preflight/backtest, backtest; evaluation / result/weights / result/trades 조회 |

주 실행은 finrl/framework.py, 비중 평가 보조는 finrl_trading/backtest.py입니다.

모든 호출은 data/Operations.tsx와 단일 /api를 사용합니다. 부모 폴더 변경 시 import 경로와 shell/Shell.tsx의 메뉴 연결을 함께 갱신합니다.
