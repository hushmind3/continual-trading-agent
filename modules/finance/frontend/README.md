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
| MoE | #finance/moe · extensions/moe/ |
| 연결 · 설정 | #finance/connection_settings · management/connection_settings/ |


사용자 메뉴는 연결·설정만 등록합니다. 진단·코드 적용 및 전체 백엔드 카탈로그는 사용자 메뉴에서 제외합니다. 공통 기능 실행에 사용하는 내부 모듈은 유지합니다.

이 폴더가 실제 finance 프론트 소유 경로입니다. 이전 frontend/src/pages/finance에는 위치 안내만 남습니다. 등록은 ../module.json → register.ts이며 호스트 렌더러·UI·단일 API 인터페이스를 사용합니다.
