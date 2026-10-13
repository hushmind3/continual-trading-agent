# REA 역공학

취합: `rea_menu_manager.py`. 이 파일만 상위 menu_registry가 import합니다.

- [프로그램 분석](analysis/README.md): analysis/
- [프로젝트 탐색](project_browser/README.md): project_browser/

설치 의존성: 이 대메뉴 폴더의 package.json·node_modules. 저장 결과: project_explorer/saved_projects/ (Git 제외). 분석 엔진은 analysis/, 저장 결과 탐색은 project_browser/에 있습니다.

취합: submenu_manager.py → rea_menu_manager.py(대메뉴 등록) → 전체 menu_registry → API. 새 기능 구현은 소속 하위 폴더에 추가하고 소메뉴 매니저에 등록합니다.

Independent backend project: backend/rea/. Its large-menu registration is imported by backend/menu_registry.py, and API delivery is backend/web_api.py. Installed node_modules remain inside this REA project.

프로그램 분석과 프로젝트 탐색은 소메뉴입니다. project_explorer/saved_projects/는 프로젝트 탐색에서 보여주는 실제 저장 결과이며 별도 대메뉴나 실행 모듈이 아닙니다.

메뉴·폴더·화면 주소 대응: 프로그램 분석 = program_analysis/ = #rea/program_analysis; 프로젝트 탐색 = project_explorer/ = #rea/project_explorer.
