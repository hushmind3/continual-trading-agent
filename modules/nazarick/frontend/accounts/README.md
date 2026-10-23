# 공용 설정 화면

용도: 플랫폼 상단 서버 연결 옆 톱니바퀴에서 여는 공용 브라우저·계정 설정입니다. 나자릭의 숨김 소메뉴 `overlord/nazarick/accounts`이며 전체 화면 주소로도 열 수 있습니다.

- `Accounts.tsx`: 공용 브라우저 시작·Google/GitHub 로그인 페이지 열기·에이전트 연결 설정·키 보관 방식 안내.
- `Services.tsx`: 업체별 가입 진행 기록·주소 일괄 추가·전용 브라우저에서 열기·키체인 저장용 비밀번호 입력. API 키는 저장 후 입력에서 지우며 응답으로 다시 조회하지 않습니다.
- `types.ts`: 소유 API 접두사와 실제 응답/진행 상태. 상태는 기록이며 자동 가입 검증으로 표시하지 않습니다.
- 등록: `../register.ts`의 `utility: settings`, `sidebar: false`. 공통 `frontend/src/shell/Shell.tsx`가 상단 아이콘·Drawer를 렌더링합니다. 기존 공통 UI와 Tailwind 테마를 사용합니다.
- 직접 API·런타임·키체인·에이전트 설정·현재 확인 범위: [실제 백엔드 안내](../../../../backend/overlord/nazarick/accounts/README.md).

확인: `npm run typecheck --workspace frontend`; 기존 적용 경로 후 어느 메뉴에서든 상단 공용 설정 아이콘 → 공용 브라우저/업체 탭을 확인합니다. 실제 로그인·가입 없이 완료로 표시하지 않습니다.
