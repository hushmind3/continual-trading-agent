# 모듈 · 도구

- 역할: FinRL 원본과 금융 프로젝트(stockrl) 모듈을 한 목록에서 검색·필터링합니다. 상태·사용 참조·import·실행 기록을 구분합니다.
- 주소: #finance/modules_tools. 프론트·백엔드 작은 메뉴 폴더 이름은 modules_tools입니다.
- 프론트 진입점: ModulesTools.tsx → 공통 FrameworkWorkspace/ModuleCatalog.
- 백엔드 등록: menu.py → finrl/submenu_manager.py → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → 단일 /api.
- 의존성: 기존 framework 뷰, NativeModuleRunner의 FinRL 원본 실행, 프로젝트 API는 all_backend_features?tab=commands로 연결합니다.
- 정리: 별도 프로젝트 모듈 메뉴·화면·등록 폴더는 의존성을 제거한 뒤 휴지통으로 이동했습니다. 실제 금융 기능·공식 원본·API 작업명·데이터는 변경하지 않았습니다.
- 확인 상태: 이번 통합 후 브라우저·타입·함수 실행 검사는 미실행입니다.

실제 모듈 목록·원본 함수 입력·실행·결과 화면은 모두 이 작은 메뉴 폴더에 있습니다: FrameworkWorkspace.tsx, NativeModuleRunner.tsx, NativeParameterFields.tsx, FrameworkResult.tsx. 공급원 설정 화면은 management/connection_settings/FrameworkProviders.tsx입니다. 금융 밖 shared/frameworks/ 구현은 없습니다.
