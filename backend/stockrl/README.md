# 프로젝트 플랫폼 백엔드

web_api.py → menu_registry.py → 대메뉴 취합 파일 → 작은 메뉴의 menu.py·handlers.py 순서로 연결합니다. 각 폴더 README를 먼저 읽습니다.

- [trading](trading/README.md)
- [finrl](finrl/README.md)
- [extensions](extensions/README.md)
- [management](management/README.md)
- [rea](rea/README.md)

- api_context.py: 공유 HTTP 객체·기존 상태 관리자 참조.
- api_transport.py: 단일 /api 전송·로컬 요청 처리·React 제공.
- platform/: 여러 메뉴가 함께 사용하는 상태·모델·장치·공식 모듈 실행 기반.
- 루트 expert_*, moe_*, multiscale.py: 학습·운영·MoE에서 공유하는 모델 계약입니다. 저장 정책의 클래스 import 경로를 유지합니다.
- finrl/framework.py와 finrl_trading/: 여러 메뉴에서 사용하는 공식 라이브러리 연결입니다.
- job_worker.py: 메뉴 구현을 실행하는 공통 작업 프로세스.

단일 /api를 유지합니다. 메뉴 등록·import·실행 확인은 서로 다릅니다. 모델·데이터·계좌·인증·설정은 재배치하지 않습니다.

Registration: feature modules → submenu_manager → large-menu registration → menu_registry → single API. New project features are registered through their own managers; the central API and existing finance implementation stay independent of that addition.
