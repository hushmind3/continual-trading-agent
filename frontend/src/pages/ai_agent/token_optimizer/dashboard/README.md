# 토큰 대시보드 화면

용도: AI 에이전트 → 토큰 최적화 → 대시보드에 실제 Codex 사용량·최적화 상태를 표시합니다.

- Dashboard.tsx: 최초 조회·수동 새로고침·집계 카드·일별 기록. manager.ts → 상위 manager.ts → register.ts로 등록합니다.
- API: ai_agent/TokenOptimizer/dashboard. 공통 request·Panel·KeyValues·Button·DataTable과 Tailwind 테마를 재사용합니다. 일별 표에 검색·페이지 버튼을 추가하지 않습니다.
- 캐시 입력을 새 입력과 분리하고, API 비용 환산·초기 지침·RTK 출력 절감이 추정임을 표시합니다. Codex 모델·계정·추론·프롬프트 설정은 변경하지 않습니다.
- 확인: 기존 8766 화면에서 실제 값·새로고침·390px 가로 넘침과 화면 오류를 확인합니다. 2026-10-26 기존 8766의 실제 화면·수동 새로고침 HTTP 200·390px 가로 넘침 없음·화면 오류 0건을 확인했습니다.
