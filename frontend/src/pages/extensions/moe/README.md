# MoE

- 역할: 화면 컴포넌트와 소속 기능. 
- 핵심 파일: ExpertDiscovery.tsx, ExpertLibraryPanel.tsx, ExpertSearchResult.tsx, ExpertVariants.tsx, ModelFiles.tsx, ModelGuide.tsx, ModelWorkspace.tsx, PrecisionTolerance.tsx, expertFamilies.ts
- 상위 연결: ../submenu_manager.ts → extensions_menu_manager.ts → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.
