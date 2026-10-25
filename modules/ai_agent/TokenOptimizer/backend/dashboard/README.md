# 토큰 대시보드 API

용도: 실제 설치 도구의 읽기 전용 집계를 단일 API로 제공합니다.

- manager.py: ai_agent/TokenOptimizer/dashboard GET 등록. refresh=true는 메모리 캐시를 갱신합니다.
- data.py: CODEX_HOME의 실제 설치 버전에서 measure.py trends --days 7 --json·quick --json, RTK gain --format json을 호출합니다. 사용자 기록을 복제하거나 모델을 호출하지 않습니다.
- 최근 7일의 입력·새 입력·캐시·출력·세션·일별 합계와 RTK 명령 출력 절감을 구분합니다. 비용은 도구의 API 가격 환산 추정이며 구독 청구액이 아닙니다. 초기 문맥 수치도 도구 추정치입니다.
- 60초 메모리 캐시만 사용합니다. 누락·실패는 오류 또는 미집계로 표시하며 0으로 대체하지 않습니다. 세션 전문·명령 인수·키는 API에 포함하지 않습니다.
- 확인: 기존 서버의 단일 /api에서 operation=ai_agent/TokenOptimizer/dashboard를 조회하고 실제 기존 Codex 집계와 화면을 확인합니다. 2026-10-26 기존 서버 API HTTP 200·실제 Codex 세션 2개·일별 기록 2행과 입력=새 입력+캐시 합계를 확인했습니다.
