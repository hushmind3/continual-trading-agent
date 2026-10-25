# 공식 기능 연결

용도: 기존 헤르메스 홈·프로필·대화·기억에 공식 관리 기능을 연결합니다.

- handlers.py → 중메뉴 manager.py → AI 에이전트 등록 → 단일 /api.
- asgi.py의 /api/ai_agent/Hermes/native/는 같은 호스트에서 공식 HTTP·파일·스트리밍과 WebSocket을 전달합니다. 브라우저 종료 시 공식 스트림도 정리합니다.
- websocket.py가 공식 연결 승인·메시지·종료를 전달하며 호스트의 기존 원격 인증과 동일 출처 검사를 유지합니다. 공식 인증 토큰은 worker 안에서만 주입합니다.
- engine/official.py는 기존 worker 안에서 원본 ASGI 앱과 게이트웨이 수명 주기를 사용합니다.
- 프론트는 frontend/settings/official/이며 원본 기능과 플랫폼 공통 디자인을 사용합니다.
- 2026-10-26 실제 확인: 원본 상태 API 200, 319개 HTTP 경로 등록, 기존 업무 보드 조회·WebSocket 연결 승인. 보드에 새 사건을 만들지 않아 사건 수신은 미확인입니다. 외부 계정·채널 전체 실행도 미확인입니다.
