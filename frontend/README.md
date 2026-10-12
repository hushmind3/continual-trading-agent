# React 개발 실행

## 구조부터 확인

| 역할 | 먼저 읽을 문서 |
| --- | --- |
| 전체 메뉴·구역·오류 표시 | [src/shell/README.md](src/shell/README.md) |
| 단일 API·공통 상태 | [src/data/README.md](src/data/README.md) |
| 기능별 화면 폴더 | [src/pages/README.md](src/pages/README.md) |
| 재사용 컴포넌트·밀도 | [src/ui/README.md](src/ui/README.md) |
| 대응 백엔드 | [backend/stockrl/README.md](../backend/stockrl/README.md) |

FinRL 메인과 FinRL-Trading 보조의 경계를 유지합니다. 새 기능 연결·파일 이동 시 해당 폴더 문서와 메뉴·오류 표시를 함께 갱신합니다.

접이식 큰 메뉴 5개 아래 작은 메뉴 15개와 백엔드 등록 추가 기능을 연결합니다. 전체 구조, 메뉴별 API, SAC·Expert·시세·가상계좌 연결 상태는 [루트 README](../README.md)를 참조합니다.

운영 접속: 루트 `서버켜기.cmd` → `http://127.0.0.1:8766/` (FastAPI + React 정적 파일).

개발 실행: `frontend`에서 `npm ci`로 잠긴 의존성을 준비한 뒤 `npm run dev` 또는 `start.cmd` → `http://127.0.0.1:5173/`. `/api`는 8766으로 전달됩니다.

React 소스는 `src/`, 공통 컴포넌트는 `src/ui/`, 화면은 `src/pages/`, API 호출과 타입은 `src/data/`에 있습니다. `dist/`는 빌드 산출물, `node_modules/`는 설치 의존성입니다. 소스와 역할이 다릅니다.

운영 화면의 `변경 적용 · 전체 점검`은 바뀐 소스만 기존 런처에서 빌드·갱신하고 실제 상태를 기록합니다. `전체 시스템 시작·중지`는 별도 운영 동작입니다. 실행 단계와 미확인 사항은 관리 화면에서 구분합니다.
