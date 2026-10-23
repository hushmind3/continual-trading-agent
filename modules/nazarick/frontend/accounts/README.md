# 공용 설정 화면

용도: 플랫폼 상단 서버 연결 옆 톱니바퀴에서 여는 공용 브라우저·계정 설정입니다. 나자릭의 숨김 소메뉴 `overlord/nazarick/accounts`이며 전체 화면 주소로도 열 수 있습니다.

- `Accounts.tsx`: 일반·계정/서비스·브라우저·에이전트 연결·API 키·데이터/보관의 실제 화면. 항목 목록·제목·순서는 `../../module.json`의 `shared_settings`에서 등록하며 이 컴포넌트는 전달받은 `page`만 렌더링합니다.
- `Services.tsx`: 업체별 가입 진행 기록·주소 일괄 추가·전용 브라우저에서 열기.
- `Credentials.tsx`: API 키 탭의 업체 선택·키체인 저장 입력. API 키는 저장 후 입력에서 지우며 응답으로 다시 조회하지 않습니다.
- `types.ts`: 소유 API 접두사와 실제 응답/진행 상태. 상태는 기록이며 자동 가입 검증으로 표시하지 않습니다.
- 등록: `../register.ts`의 `settingsPage`와 모듈 명세의 `shared_settings`. 공통 `frontend/src/shell/module_loader.ts`가 모든 활성 모듈의 항목을 자동 취합하고 `SharedSettings.tsx`가 담당 화면에 `page/navigate`를 전달합니다. 상단 아이콘은 등록된 항목이 있을 때 표시하며 넓은 중앙 설정창·분류 탐색은 공통 `SettingsWorkspace`와 `Drawer variant=settings`를 사용합니다. 새 모듈의 설정을 추가할 때 Shell·공용 탭 목록을 직접 고치지 않습니다. 숨김 주소는 `sidebar: false`이며 같은 공용 설정창 내용을 렌더링합니다.
- 직접 API·런타임·키체인·에이전트 설정·현재 확인 범위: [실제 백엔드 안내](../../../../backend/overlord/nazarick/accounts/README.md).

확인: `npm run typecheck --workspace frontend`; 프론트 빌드 후 `development/scripts/start_server.py --apply-only --frontend-only --skip-build`로 기존 서버의 화면만 적용합니다. 어느 메뉴에서든 상단 아이콘 → 등록된 여섯 항목을 선택해 담당 화면을 확인합니다. 실제 로그인·가입 없이 완료로 표시하지 않습니다.

2026-10-24 실제 확인: 타입 검사·Vite 빌드·프론트 독립 적용 성공. 실제 8766 설정창에서 모듈 명세로 등록한 여섯 탭의 선택과 담당 내용 표시를 확인했습니다. 기존 금융 명세의 `settings`와 충돌하지 않도록 공용 설정은 `shared_settings`를 사용합니다. 로그인·업체 가입·키 저장은 이번 화면 개편에서 실행하지 않았습니다.
