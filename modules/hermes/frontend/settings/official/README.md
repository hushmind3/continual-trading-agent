# 공식 기능의 플랫폼 화면

용도: 공식 React 기능을 기존 헤르메스 설정 탭과 공통 디자인으로 제공합니다.

- OfficialWorkspace.tsx: 원본 페이지·프로필·플러그인·한국어 문맥.
- ResumeSession.tsx: 기본 프로필의 대화 기록을 기존 플랫폼 대화로 이어갑니다.
- transport.ts: 실제 공식 HTTP·파일·WebSocket을 같은 /api/ai_agent/Hermes/native/에 연결합니다.
- frontend/official-vite.ts: 원본 모듈 경로·전송 경계만 연결하고 버전 관리된 한글 패치를 준비합니다.
- 디자인·글꼴은 frontend/src/tailwind.css를 공유합니다. 기존 주 대화와 사업·직원·회의 기능을 유지합니다.
- backend/native/ → 기존 worker → 공식 ASGI 앱. 기존 runtime/ai_agent/Hermes를 사용합니다.
- 2026-10-26: 실제 모델·스킬·업무 보드 화면, WebSocket 연결 승인, Pretendard 공통 글꼴·흰색 배경·가로 넘침 없음·화면 오류 0건 확인. 타입 검사·Vite 빌드 통과. 외부 인증이 필요한 전체 기능의 실제 실행은 미확인입니다.
