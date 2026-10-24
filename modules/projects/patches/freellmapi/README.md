# FreeLLMAPI 화면·Codex 호환 패치

용도: 원본 FreeLLMAPI의 기본 화면을 작은 요약 대시보드로 바꿔, 업체가 보고한 잔여 한도, 저장된 연결 전체 수, 현재 자동 라우팅 후보, 가장 최근 요청의 결과를 구분해 표시합니다. 월 한도나 로컬 사용 기록으로 실제 잔액을 추정하지 않습니다. 모델별 차트와 요청 통계는 기본 화면에서 제외하고 페이지 스크롤을 만들지 않습니다. 고급 설정은 접어 둡니다.

- `usage-overview.patch`: 원본 React의 App.tsx, FallbackPage.tsx, usage-overview.tsx 변경. 공통 Card 컴포넌트와 Tailwind 테마를 사용하고, 제공업체 이름은 `/api/keys/providers` 메타데이터에서 읽습니다.
- 저장 현황: `/api/keys`의 응답을 사용해 FreeLLMAPI에 저장된 제공업체 수와 키 항목 수를 보여줍니다. 이 수는 외부 사이트 가입 수나 사용 가능 키 수와 같지 않습니다.
- 잔액: `/api/free-tier`가 반환하는 업체 보고 잔여량만 단위별로 표시합니다. 보고값이 없는 업체는 “잔여량 미보고”로 표시하고 월 카탈로그 한도나 로컬 요청 기록으로 대신하지 않습니다.
- 자동 라우팅: `/api/fallback`에서 키가 있고 활성화된 모델만 표시하며 모델 수와 제공업체 수를 따로 셉니다. 같은 기반 모델이 여러 제공업체에 있으면 각 제공업체의 라우팅 항목으로 표시됩니다.
- 최근 요청: analytics API에서 최근 24시간의 마지막 완료 요청을 가져와 성공·실패·취소, 모델, 시각 및 시도 횟수를 표시하고 5초마다 갱신합니다. 현재 진행 중인 요청의 순간별 시도 상태는 표시하지 않습니다.
- 설치 소유: runtime/projects/manage/projects/freellmapi/versions/version-1/source/. 기준 원본 커밋: 26484157fd15f5fb66f54d3a86f568997ea304de.
- 업데이트 후 원본에서 `git apply --check <패치 절대 경로>` 성공 시 `--check` 없이 적용하고 client에서 `VITE_BASE=/assets/projects/<설치 ID>/ npm run build`로 빌드합니다. 충돌하면 강제 적용하지 않습니다. 자동 재적용은 미구현입니다.

확인: 기존 설치의 TypeScript·Vite 빌드와 Codex 안의 실제 화면을 확인합니다. 2026-10-24 설치 경로용 빌드 성공. 실제 화면에서 저장된 제공업체 24곳·키 항목 31개, 자동 라우팅 5개 제공업체·6개 모델, 보고 잔여량 8,000 토큰 및 0 요청이 표시되는 것을 확인했습니다. 키 항목 수는 비활성·문제 키를 포함할 수 있습니다. API가 잔여량을 보고하지 않는 업체에는 추정값을 표시하지 않습니다.

## Codex 도구 호환

`codex-compatibility.patch`는 원본 `server/src/lib/gemini-wire.ts`의 Gemini 도구 스키마 변환에서 Codex의 `encrypted` 주석만 제거합니다. 실제 인수 이름이 encrypted인 경우는 보존합니다. 기존 `server/src/__tests__/lib/gemini-wire.test.ts`에 중첩 배열·객체·nullable 인수 회귀 검사를 포함합니다. 업데이트 후 원본에서 패치를 적용하고 기존 server 디렉터리에서 `npm run build`로 컴파일해야 합니다.

2026-10-24 실제 확인: 관련 기존 검사 21개·서버 TypeScript 빌드 통과. 중첩 encrypted 주석을 가진 함수 도구 6개를 OpenCodex → 기존 단일 API → FreeLLMAPI → Google 자동 경로에 전달했고, 실제 현재 폴더를 읽어 도구 결과를 반환하는 두 요청이 completed로 끝났습니다. 이어 설치 키로 같은 loopback `/v1/responses` 경로를 호출해 auto의 일반 응답과 `encrypted` 필드를 포함한 함수 호출 완료를 확인했습니다. 이는 Codex 데스크톱의 장시간 대화·모든 도구를 전부 확인한 결과는 아닙니다.

플랫폼 연결의 큰 부가 헤더는 원본 Node 서버의 헤더 상한을 초과해 write EPIPE를 재현했습니다. `modules/projects/backend/handlers.py`가 원본에 필요한 인증·본문·User-Agent·요청 ID 헤더만 전달하도록 수정했습니다. 32 KiB 부가 헤더와 3 MiB 본문을 가진 실제 기존 models 요청이 수정 후 HTTP 200을 반환했습니다. 모델 추론을 하지 않는 전송 확인입니다.

FreeLLMAPI API 응답은 `modules/projects/backend/node_http_worker.cjs`에서 통째로 버퍼링하지 않고, 요청이 `stream: true`를 지정하면 IPC 청크를 `StreamingResponse`로 전달합니다. 스트리밍 연결은 10분 무응답 제한, 비스트리밍 Node HTTP 요청은 15분 제한 및 64 MiB 응답 상한을 사용합니다. 2026-10-24 `auto`에 짧은 스트리밍 요청을 보내 HTTP 200, 첫 SSE 이벤트 약 1.4초, 완료 이벤트 수신을 확인했습니다. 장시간 작업 경계값(10/15분)은 실제로 기다려 검증하지 않았습니다.

## 자동 로그인·공용 클라이언트 복구

2026-10-25 원인: 공유 IPC 응답 큐에 이전 응답이 남아 모델 목록·인증 상태·세션 발급 응답이 한 요청씩 밀렸습니다. `modules/projects/backend/{runtime.py,node_http_worker.cjs}`가 요청 ID와 전용 응답 큐를 사용하도록 고쳤습니다. 취소된 스트림의 남은 이벤트는 다음 호출로 전달하지 않습니다. 원본 로그인 화면을 감추거나 인증을 해제하지 않으며, 기존 `FREEAPI_DESKTOP=1`의 공식 로컬 세션 발급을 유지합니다.

실제 확인: 단일 API에서 인증 상태 → 자동 세션 발급 → 인증 완료 상태가 각 요청에 맞는 JSON을 반환했고, Codex 안의 기존 대시보드가 로그인 입력 없이 요약 화면을 표시했습니다. 기존 Hermes 기본 프로필 CLI와 OpenClaw dev Gateway에서 `auto`가 응답했습니다. OpenClaw는 실제 응답 모델 `gemini-2.5-flash`를 기록했습니다. Hermes의 lead 웹 화면에도 공식 공용 제공자를 선택해 `auto` 응답을 확인했습니다. 잔액은 원본 API 보고값으로만 표시하며 업체 청구 대시보드를 전수 확인한 결과는 아닙니다.
