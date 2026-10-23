# 나자릭 중메뉴

용도: 연결 업체를 미리 정하지 않고 연결 정의·어댑터 규격·확인 기록을 공유하는 본체의 첫 버전입니다.

## 현재 구현

- `manager.py`가 [개요](overview/README.md), [연결 대상](connections/README.md), [작업 기록](activity/README.md) 소메뉴 매니저를 import합니다. `../manager.py`가 오버로드 대메뉴로 취합합니다.
- `store.py`: `runtime/overlord/nazarick/foundation.sqlite3`에 연결 정의와 작업 기록을 저장합니다. 소스·비밀키와 분리합니다.
- `adapters.py`: `Adapter`의 `targets/inspect` 규격과 명시적인 `ADAPTERS` 등록표. 현재 제공하는 `platform_module`은 기존 서버에 로드된 모듈의 등록·API 규격만 읽습니다. 엔진·모델·업무를 실행하지 않습니다.
- 화면은 `modules/nazarick/frontend/`에 있습니다. 공통 React/Vite/Tailwind/UI와 `/api` 전송기를 재사용합니다.
- 확장 영역은 실행·데이터·계정·결제·유통·사용자 확장입니다. 외부 서비스는 어댑터 미구현을 명시한 `planned` 상태이며, 연결 성공으로 표시하지 않습니다.

외부 어댑터를 추가할 때는 공급자별 실제 구현·허용 설정·확인 방법을 함께 구현하고 등록표와 입력 계약을 확장합니다. 화면의 이름 등록만으로 외부 연결이 만들어지지 않습니다. 임의 코드·모듈명 실행과 비밀키 입력은 제공하지 않습니다.

## 실행과 확인

기존 `서버켜기.command`의 단일 서버를 사용합니다. 화면 `http://127.0.0.1:8766/#overlord/nazarick/overview`, API operation `overlord/nazarick/overview`.

`npm run typecheck --workspace frontend`; 빌드·서버 적용은 기존 `development/scripts/start_server.py --apply-only` 경로를 사용합니다. 실제 화면에서 기존 플랫폼 기능을 등록 → 등록 확인 → 새로고침 → 기록 조회로 확인합니다. 확인용 새 제품·별도 서버·모델 호출은 필요하지 않습니다.

2026-10-24 실제 확인: TypeScript·Vite 빌드와 기존 8766 서버 적용 완료. 실제 브라우저에서 기존 프로젝트 관리 모듈을 대상 등록 → 등록 확인 → 새로고침 후 보존 → 작업 기록 표시까지 확인했습니다. 1440px/390px 화면의 가로 넘침과 JavaScript 오류는 없었습니다. 존재하지 않는 연결은 HTTP 404, 허용하지 않는 추가 입력 필드는 HTTP 422로 거절했습니다. 화면은 `runtime/overlord/nazarick/verification/`에 보관합니다. 별도 제품·서버·재설치·모델 호출은 수행하지 않았습니다.

미구현: 외부 클라우드·인증·결제·범용 업무 실행과 외부 고객 제공. 현재 성공 표시는 플랫폼 모듈의 등록 확인 범위에 한정됩니다.
