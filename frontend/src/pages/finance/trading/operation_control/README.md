# 운영 제어

- 역할: 화면 컴포넌트와 소속 기능. 
- 핵심 파일: OperationControl.tsx
- LearningProgress.tsx: 입력 최신 시각, 이번 입력의 학습 대기 봉 수, 직전 소비 시각, 완료된 학습의 실제 소비 시각·단계 및 운영 반영을 표시합니다. 최신 소비 범위 표시의 TypeScript·빌드·브라우저 검사·서버 적용은 미실행입니다.
- 상위 연결: ../submenu_manager.ts → finance_menu_manager.ts → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.

- 주소: `#finance/operation_control`. 메뉴 등록 ID와 프론트 폴더 이름을 일치시킵니다.
