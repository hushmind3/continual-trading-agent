# 백엔드 API

- 화면: `BackendApiPage.tsx`, 스타일: `BackendApiPage.css`.
- 등록: `backend_menu_manager.ts` → 전체 `menu_registry.ts`.
- 주소: `#backend/api`. 프론트 메뉴는 백엔드 API 하나입니다.
- 의존성: `swagger-ui-react`, FastAPI `/openapi.json`.
- 문서는 실제 등록된 핸들러의 입력 스키마로 생성하며, 실행 요청은 기존 단일 `/api`를 사용합니다.
- 화면 진입만으로 업무 명령을 실행하지 않습니다. 사용자가 Swagger의 실행 버튼을 눌러야 요청합니다.
