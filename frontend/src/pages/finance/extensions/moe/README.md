# MoE

- 역할: 화면 컴포넌트와 소속 기능. 
- 핵심 파일: ExpertDiscovery.tsx, ExpertLibraryPanel.tsx, ExpertSearchResult.tsx, ExpertVariants.tsx, ModelFiles.tsx, ModelGuide.tsx, Moe.tsx, PrecisionTolerance.tsx, expertFamilies.ts
- 상위 연결: ../submenu_manager.ts → finance_menu_manager.ts → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.

- 주소: `#finance/moe`. 메뉴 등록 ID와 프론트 폴더 이름을 일치시킵니다.

다운로드 버튼은 원본 저장·자동 등록을 수행하고 실제 경로를 표시합니다. 실행기 미확인은 다운로드 차단 조건이 아닙니다. 전체 검사에는 기본 켜진 중복 검사 제외 옵션이 있으며, 선택 버전 삭제는 모델 카드에만 있습니다. 이미 존재하는 정밀도는 재양자화·재검사하지 않습니다. 원본 등록·실행기 미설정 자료는 Frozen 가중치와 구분해 표시합니다.
