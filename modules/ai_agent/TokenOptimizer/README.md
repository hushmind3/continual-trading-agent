# 토큰 최적화

용도: 설치된 Token Optimizer·RTK의 실제 Codex 집계를 플랫폼의 별도 대시보드 메뉴에 표시합니다. 새 사용량 DB나 별도 API 서버를 만들지 않습니다.

- 연결: backend/dashboard/manager.py → backend/manager.py → backend/ai_agent/manager.py → 모듈 등록 → 단일 /api.
- 화면: frontend/dashboard/Dashboard.tsx → 소메뉴·중메뉴 매니저 → 자동 메뉴 등록.
- 자세한 데이터·확인 범위는 [백엔드](backend/dashboard/README.md), 화면은 [프론트엔드](frontend/dashboard/README.md)를 따릅니다.

2026-10-26 확인: 실제 단일 API·기존 Codex 기록·RTK JSON 집계와 수동 새로고침 HTTP 200, 데스크톱·390px 표시 및 오류·가로 넘침 없음을 확인했습니다. 초기 문맥·API 비용·명령 출력 절감은 표시된 범위의 추정이며 실제 구독 청구액·모델 전체 절감률과 다릅니다.
