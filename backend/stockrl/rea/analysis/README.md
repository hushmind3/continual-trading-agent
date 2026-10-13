# 프로그램 분석

- 역할: menu.py: 메뉴 등록; handlers.py: 기존 API 처리. 
- 핵심 파일: artifacts.mjs, bridge.mjs, extract.py, handlers.py, menu.py, operations.py
- 상위 연결: ../submenu_manager.py → rea_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.

operations.py는 설치된 원본 REA CLI/MCP·Ghidra와 연결하며 extract.py는 원문 추출·분석 저장만 수행합니다. bridge.mjs·artifacts.mjs도 이 폴더에 있습니다. 코딩 에이전트·재구현·추출 프로그램 실행은 자동 호출하지 않습니다.
