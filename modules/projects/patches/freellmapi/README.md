# FreeLLMAPI 화면·Codex 호환 패치

용도: 기존 원본 UI의 기본 화면에 업체명·모델명·각 모델의 남은 무료 토큰 추정 총량만 공통 목록으로 표시합니다. 페이지 스크롤·차트·요청 수·사용량 목록은 기본 화면에서 제외합니다. 고급 설정과 원본 코드는 삭제하지 않고 접어 둡니다. 최근 성공한 실제 업체·모델은 기존 analytics/requests API에서 읽어 5초마다 갱신합니다.

- `usage-overview.patch`: 원본 React의 App.tsx, FallbackPage.tsx, usage-overview.tsx 변경. 기존 Tailwind 테마와 전체 높이 레이아웃을 사용합니다.
- 데이터: 원본 `/api/fallback` 활성 모델과 `/api/fallback/token-usage`의 모델별 월 카탈로그 한도에서 로컬 사용량을 뺀 잔여량입니다. 고정 모델명·개수 없이 새 활성 모델도 같은 공통 행으로 표시합니다.
- 제한: 공급업체 계정의 실제 잔액이 아니며 미제공 한도는 합산하지 않습니다. 일일/분당 제한이나 공급업체 공유 한도로 전부 소진하지 못할 수 있으므로 실제 사용 가능한 크레딧으로 보장하지 않습니다. 화면에 추정·실제 잔액 미연동을 표시합니다.
- 설치 소유: runtime/projects/manage/projects/freellmapi/versions/version-1/source/. 기준 원본 커밋: 26484157fd15f5fb66f54d3a86f568997ea304de.
- 업데이트 후 원본에서 `git apply --check <패치 절대 경로>` 성공 시 `--check` 없이 적용하고 client에서 `VITE_BASE=/assets/projects/<설치 ID>/ npm run build`로 빌드합니다. 충돌하면 강제 적용하지 않습니다. 자동 재적용은 미구현입니다.

확인: 기존 설치의 TypeScript·Vite 빌드와 Codex 안의 실제 화면을 확인합니다. 화면 수정 검증용 모델 호출은 하지 않습니다. 실제 업체 잔액은 미확인입니다.

## Codex 도구 호환

`codex-compatibility.patch`는 원본 `server/src/lib/gemini-wire.ts`의 Gemini 도구 스키마 변환에서 Codex의 `encrypted` 주석만 제거합니다. 실제 인수 이름이 encrypted인 경우는 보존합니다. 기존 `server/src/__tests__/lib/gemini-wire.test.ts`에 중첩 배열·객체·nullable 인수 회귀 검사를 포함합니다. 업데이트 후 원본에서 패치를 적용하고 기존 server 디렉터리에서 `npm run build`로 컴파일해야 합니다.

2026-10-24 실제 확인: 관련 기존 검사 21개·서버 TypeScript 빌드 통과. 중첩 encrypted 주석을 가진 함수 도구 6개를 OpenCodex → 기존 단일 API → FreeLLMAPI → Google 자동 경로에 전달했고, 실제 현재 폴더를 읽어 도구 결과를 반환하는 두 요청이 completed로 끝났습니다. 이는 Codex 화면에서 모든 기능을 확인한 결과는 아닙니다.

플랫폼 연결의 큰 부가 헤더는 원본 Node 서버의 헤더 상한을 초과해 write EPIPE를 재현했습니다. `modules/projects/backend/handlers.py`가 원본에 필요한 인증·본문·User-Agent·요청 ID 헤더만 전달하도록 수정했습니다. 32 KiB 부가 헤더와 3 MiB 본문을 가진 실제 기존 models 요청이 수정 후 HTTP 200을 반환했습니다. 모델 추론을 하지 않는 전송 확인입니다.
