# 큰 메뉴별 연결 파일

menu_registry.ts는 큰 메뉴 연결 파일 5개만 import합니다. 각 파일은 자기 아래 화면만 연결하며 Shell.tsx는 최종 등록표만 사용합니다.

- trading_menu_manager.ts: 거래 운영
- finrl_menu_manager.ts: FinRL · 메인
- finrl_trading_menu_manager.ts: FinRL-Trading · 보조
- extensions_menu_manager.ts: 프로젝트 확장
- management_menu_manager.ts: 연결 · 관리

백엔드 추가 기능은 menu_catalog의 실제 등록 정보로 자동 표시합니다. 기존 화면과 실행 기능은 제거하지 않습니다.

각 큰 메뉴 매니저의 registeredMenus가 자기 구역의 추가 기능 작은 메뉴를 연결합니다. menu_registry.ts는 이 매니저들만 모으며 Shell.tsx는 등록 결과를 표시합니다. 백엔드 기능 전체 화면도 management_menu_manager.ts에서 연결합니다.

원본 소스는 실행 메뉴와 큰 구역을 분리합니다. FinRL 메인 소스, FinRL-Trading 보조 소스, 프로젝트 백엔드 소스 아래에 source_modules의 모든 항목을 작은 메뉴로 표시합니다. 실행 여부·공개 함수 존재 여부로 목록을 필터링하지 않습니다.
