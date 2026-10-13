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

접이식 큰 메뉴 5개 아래 작은 메뉴 11개와 백엔드 등록 추가 기능을 연결합니다. 전체 구조, 메뉴별 API, SAC·Expert·시세·가상계좌 연결 상태는 [루트 README](../README.md)를 참조합니다.

운영 접속: 루트 `서버켜기.cmd` → `http://127.0.0.1:8766/` (FastAPI + React 정적 파일).

개발 실행: `frontend`에서 `npm ci`로 잠긴 의존성을 준비한 뒤 `npm run dev` 또는 `start.cmd` → `http://127.0.0.1:5173/`. `/api`는 8766으로 전달됩니다.

React 소스는 `src/`, 공통 컴포넌트는 `src/ui/`, 화면은 `src/pages/`, API 호출과 타입은 `src/data/`에 있습니다. `dist/`는 빌드 산출물, `node_modules/`는 설치 의존성입니다. 소스와 역할이 다릅니다.

운영 화면의 `변경 적용 · 전체 점검`은 바뀐 소스만 기존 런처에서 빌드·갱신하고 실제 상태를 기록합니다. `전체 시스템 시작·중지`는 별도 운영 동작입니다. 실행 단계와 미확인 사항은 관리 화면에서 구분합니다.

## 자동검증

`npm run typecheck`, `npm run build`, `npm run test:api`로 타입·운영 빌드·전송 회귀 4개를 검사합니다. 실행 중인 로컬 서버 `http://127.0.0.1:8766`에서 `npm run test:browser`는 현재 등록된 화면·시장 표 페이지 이동과 구역별 오류/진단 표시를 검사합니다. Chromium은 `npx playwright install chromium`으로 준비하며 `FINRL_BASE_URL`로 검사 주소를 지정할 수 있습니다. 로그·스크린샷·trace는 Git 제외 결과 폴더에 남습니다. 일반 요청은 60초, Champion 생성은 30분 제한이며 모듈 오류는 관련 구역과 공통 진단에 표시합니다.

Windows lock에서 누락된 Linux Rollup 등 플랫폼별 선택 의존성을 보완했습니다. 기존 패키지 버전은 유지하고, 깨끗한 검증 디렉터리에서 npm이 해석한 공식 플랫폼 패키지 기록을 lock에 반영합니다.

미사용 설치 정리: 임시 검증 디렉터리의 node_modules 2곳과 현재 Windows Node가 사용하지 않는 `@rollup/rollup-win32-x64-gnu` 설치 폴더를 프로젝트 휴지통의 동일 상대 경로로 이동했습니다. 실제 사용하는 MSVC 패키지와 플랫폼별 lock 기록은 유지합니다. 새 설치 시 npm이 선택 패키지를 다시 설치할 수 있습니다.

FinRL 메인에는 정책 학습과 FinRL 모듈·도구만 남습니다. 정책 평가 화면·StockTradingEnv 예제 화면·관련 추가 기능 5개는 등록과 전용 파일을 모두 제거했습니다. 폐기한 화면의 hash/API 연결도 제거했습니다.

FinRL-Trading의 이미지에 지정된 13개 추가 메뉴와 전용 입력폼은 제거했습니다. 남은 추가 메뉴 5개와 원본 모듈·도구 화면은 유지하며 메뉴와 입력은 백엔드 등록표에서 동일하게 생성합니다. 현재 전체 화면은 16개입니다.

REA 큰 메뉴와 분석·진단 작은 메뉴를 추가했습니다. 기본 작은 메뉴 12개·추가 메뉴 5개로 총 17개 화면이며 원본 REA 스키마/입력/결과를 표시합니다. REA 실행은 사용자 버튼 요청으로만 호출하고 원본 미지원·엔진 부족 오류를 그대로 보여줍니다.

## npm workspace

실제 node_modules와 package-lock.json은 프로젝트 루트에 있습니다. 이 폴더의 package.json은 React/Vite workspace 선언입니다. 루트에서 npm ci, npm run dev --workspace frontend, npm run build --workspace frontend를 사용합니다.
