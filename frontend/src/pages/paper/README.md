# 가상계좌·주문

| 항목 | 내용 |
| --- | --- |
| 담당 메뉴 | 가상계좌·주문 |
| 주요 파일 | PaperWorkspace.tsx / PaperAccounts.tsx |
| 역할 | 통화별 계좌·보유·원장·가상 주문 |
| 기존 API operation/조회 | orders; state의 operations 조회 |

수신 시세와 저장 가격, 계좌와 백테스트를 구분합니다.

모든 호출은 data/Operations.tsx와 단일 /api를 사용합니다. 부모 폴더 변경 시 import 경로와 shell/Shell.tsx의 메뉴 연결을 함께 갱신합니다.
