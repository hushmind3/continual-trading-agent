# REA 역공학

용도: 해당 모듈 프론트 소메뉴의 구현 위치·등록 계층과 API 연결을 안내합니다.

취합: `rea_menu_manager.ts`. register.ts가 취합하며 module.json의 프론트 진입점을 통해 자동 등록합니다.

- [프로그램 분석](program_analysis/README.md): program_analysis/
- [프로젝트 탐색](project_explorer/README.md): project_explorer/

취합: submenu_manager.ts → rea_menu_manager.ts(대메뉴 등록) → 전체 menu_registry → API. 새 기능 구현은 소속 하위 폴더에 추가하고 소메뉴 매니저에 등록합니다.

메뉴·폴더·화면 주소 대응: 프로그램 분석 = program_analysis/ = #rea/program_analysis; 프로젝트 탐색 = project_explorer/ = #rea/project_explorer.

이 폴더가 실제 rea 프론트 소유 경로입니다. 이전 frontend/src/pages/rea에는 위치 안내만 남습니다. 등록은 ../module.json → register.ts이며 호스트 렌더러·UI·단일 API 인터페이스를 사용합니다.
