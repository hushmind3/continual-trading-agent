# 백엔드 기능 전체

- 역할: menu.py: 메뉴 등록; handlers.py: 기존 API 처리. 
- 핵심 파일: handlers.py, menu.py
- 상위 연결: ../submenu_manager.py → finance_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.

프론트 메뉴 주소: `#finance/all_backend_features`; 화면: `modules/finance/frontend/management/all_backend_features/AllBackendFeatures.tsx`. 백엔드 폴더·import 이름은 프론트 소메뉴 폴더와 일치합니다. API 작업명은 유지합니다.

모듈·도구 소메뉴를 흡수했습니다. 원본 모듈·함수 탭의 목록(FrameworkWorkspace/ModuleCatalog), 입력(NativeParameterFields), 실행(NativeModuleRunner), 결과(FrameworkResult)는 같은 프론트 폴더에 있습니다. 별도 modules_tools 메뉴·폴더는 없습니다.

2026-10-14: 원본 함수 요청의 dict/set 비교 오류와 공급원 이름 덮어쓰기를 수정했습니다. 정상 요청이 단일 /api를 통해 작업으로 전달되는지 가짜 작업 실행기로 확인했습니다. 모든 등록 명령의 메뉴 ID가 현재 9개 메뉴에 속합니다. 실제 공식 FinRL data_split은 임시 CSV로 호출했습니다.

런타임: `runtime/finance/all_backend_features/results/`. 원본 모듈 수동 실행 결과·그림을 이 소메뉴에 저장합니다. 실행 요청은 기존 공통 작업 실행기를 사용하며 별도 API 서버는 만들지 않습니다.
