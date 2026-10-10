# React 개발 실행

흰색 테마와 7개 메뉴는 f153957 React 구성을 유지합니다. 전체 구조, 메뉴별 API, SAC·Expert·시세·가상계좌 연결 상태는 [루트 README](../README.md)를 참조합니다.

운영 접속: 루트 `서버켜기.cmd` → `http://127.0.0.1:8766/` (FastAPI + React 정적 파일).

개발 실행: `frontend`에서 `npm ci`로 잠긴 의존성을 준비한 뒤 `npm run dev` 또는 `start.cmd` → `http://127.0.0.1:5173/`. `/api`는 8766으로 전달됩니다.

React 소스는 `src/`, 공통 컴포넌트는 `src/ui/`, 화면은 `src/pages/`, API 호출과 타입은 `src/data/`에 있습니다. `dist/`는 빌드 산출물, `node_modules/`는 설치 의존성입니다. 소스와 역할이 다릅니다.

이번 복구 변경에서는 테스트·빌드·화면 자동화를 실행하지 않았습니다. 이미 실행 중인 서버와 기존 `dist/`에는 새 소스가 자동 적용되지 않습니다.
