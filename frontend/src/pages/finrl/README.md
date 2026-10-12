# FinRL 주식거래 기능

| 항목 | 내용 |
| --- | --- |
| 담당 메뉴 | FinRL 주식거래 기능 |
| 주요 파일 | ReferenceWorkspace.tsx / FinrlWorkspace.tsx |
| 역할 | 데이터 준비 → 알고리즘 학습 → 백테스트 |
| 기존 API operation/조회 | framework/stock_data, framework/stock_train, framework/stock_backtest; finrl 조회 |

백엔드 finrl/operations.py에 대응합니다. 기존 데이터·모델·결과 선택과 공식 설정을 유지합니다.

모든 호출은 data/Operations.tsx와 단일 /api를 사용합니다. 부모 폴더 변경 시 import 경로와 shell/Shell.tsx의 메뉴 연결을 함께 갱신합니다.
