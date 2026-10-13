# 금융

취합: submenu_manager.ts → finance_menu_manager.ts → 전체 메뉴 매니저.

- [trading/](trading/README.md): 운영 제어·가상계좌.
- [finrl/](finrl/README.md): 정책 학습·통합 모듈 도구.
- [extensions/](extensions/README.md): MoE.
- [management/](management/README.md): 연결·설정·진단·백엔드 기능.

대메뉴 표시는 금융 하나입니다. 기능·API 작업명은 유지하며 메뉴 주소는 #finance/<영문 작은 메뉴 이름>으로 통일합니다. 이번 변경 후 브라우저·타입·기능 검사는 미실행입니다.

| 메뉴 | 주소·폴더 이름 |
| --- | --- |
| 운영 제어 | #finance/operation_control · trading/operation_control/ |
| 가상계좌 · 주문 | #finance/virtual_account_orders · trading/virtual_account_orders/ |
| 정책 학습 | #finance/policy_learning · finrl/policy_learning/ |
| 모듈 · 도구 | #finance/modules_tools · finrl/modules_tools/ |
| MoE | #finance/moe · extensions/moe/ |
| 연결 · 설정 | #finance/connection_settings · management/connection_settings/ |
| 진단 · 로그 · 코드 적용 | #finance/diagnostics_logs_code_apply · management/diagnostics_logs_code_apply/ |
| 백엔드 기능 전체 | #finance/all_backend_features · management/all_backend_features/ |
