# 큰 메뉴별 연결 파일

menu_registry.ts는 큰 메뉴 연결 파일 5개만 import합니다. 각 파일은 자기 아래 화면만 연결하며 Shell.tsx는 최종 등록표만 사용합니다.

- trading_menu_manager.ts: 거래 운영
- finrl_menu_manager.ts: FinRL · 메인
- extensions_menu_manager.ts: 프로젝트 확장
- management_menu_manager.ts: 연결 · 관리

백엔드 추가 기능은 menu_catalog의 실제 등록 정보로 자동 표시합니다. 기존 화면과 실행 기능은 제거하지 않습니다.

각 큰 메뉴 매니저의 registeredMenus가 자기 구역의 추가 기능 작은 메뉴를 연결합니다. menu_registry.ts는 이 매니저들만 모으며 Shell.tsx는 등록 결과를 표시합니다. 백엔드 기능 전체 화면도 management_menu_manager.ts에서 연결합니다.

REA 큰 메뉴는 rea_menu_manager에 등록하며 분석·진단 화면과 rea API를 연결합니다.
