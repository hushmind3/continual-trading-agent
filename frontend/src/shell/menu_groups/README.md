# 큰 메뉴별 연결 파일

menu_registry.ts는 큰 메뉴 연결 파일 5개만 import합니다. 각 파일은 자기 아래 화면만 연결하며 Shell.tsx는 최종 등록표만 사용합니다.

- trading_menu_manager.ts: 거래 운영
- finrl_menu_manager.ts: FinRL · 메인
- finrl_trading_menu_manager.ts: FinRL-Trading · 보조
- extensions_menu_manager.ts: 프로젝트 확장
- management_menu_manager.ts: 연결 · 관리

백엔드 추가 기능은 menu_catalog의 실제 등록 정보로 자동 표시합니다. 기존 화면과 실행 기능은 제거하지 않습니다.
