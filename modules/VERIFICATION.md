# 모듈 등록·탈착 확인 — 2026-10-16

완료한 범위:

- Hermes 프로그램을 `modules/hermes/backend`와 `frontend`로 이동했습니다. 기존 추적 파일 1,923개의 대응 파일이 모두 존재합니다.
- 실제 서버에서 Hermes 폴더를 분리하면 모듈 목록·현재 프론트 진입 빌드에서 빠지고 해당 세션 API가 404를 반환했습니다. 금융·REA 등록은 유지됐습니다.
- 폴더를 복원하자 공통 감시기가 자동 빌드·적용했습니다. 설정 JSON·config.yaml·state.db 해시가 유지됐고 세션 조회가 복원됐습니다. 탈착 검사 도중 중앙 코드 수정은 0건입니다.
- 별도 검사 모듈의 대메뉴·React 화면·API도 폴더 추가만으로 자동 등록됐습니다. 단일 `/api`로 응답한 후 폴더 분리 시 제거됐습니다. 중앙 코드 수정은 0건입니다.
- TypeScript 검사·Vite 빌드, 모듈 단위 검사 4개, 서버 복구 검사 4개, 실행 권한 검사 4개, 이식된 원본 엔진의 컨텍스트 연결 검사 1개가 통과했습니다. 마지막 검사는 가짜 모델 응답으로 연결을 확인한 것이며 실제 GGUF 추론은 실행하지 않았습니다.
- 1440px 브라우저에서 복원된 Hermes 화면과 메뉴를 열어 확인했습니다. pageerror 0건이며 학습·가상매매·실제 주문은 실행하지 않았습니다.

실행 명령은 `development/scripts/verify_module_detach.py`와 `verify_module_registration.py`입니다. 원시 결과·스크린샷은 Git 제외 `runtime/platform/`의 `module-verification.json`, `module-registration-verification.json`, `module-ui.png`에 있습니다.

미완료 범위:

- 금융·REA는 기존 코드를 사용하는 등록 어댑터입니다. 전체 코드의 완전한 탈착·독립 실행은 확인하지 않았습니다.
- 모듈 폴더 탈착은 독립 배포 패키지 생성과 다릅니다. 공통 호스트·UI·Python 환경을 포함한 독립 배포 생성·검증은 미완료입니다.
- 외부 GitHub 저장소의 최초 자동 변환, 공통 프로젝트 협업 도구, Expert의 공통 모듈 규격은 미완료입니다.
