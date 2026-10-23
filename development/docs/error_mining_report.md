# 프로젝트 오류 채굴 보고서

- 용도: backend/stockrl·web_api·api_·rea, frontend/의 실제 실행 오류와 정적 분석 결과를 정리.
- 기준: 2026-10-16. 검사 도구 — Python `compileall`(문법), `.venv/Scripts/python.exe`(실제 import), `uvicorn`(실행), `tsc --noEmit`(타입), Playwright, `ruff`(정적 분석).
- 범위: Hermes 엔진(`backend/ai_agent/Hermes/`)은 제3자 바운드 코드이므로 제외. `.venv/`·`.git/`·`runtime/`·`node_modules/`·`__pycache__` 제외.

## 결론

- **실행 경로에는 실제 오류가 없음.** FastAPI 서버가 실제로 구동되고, 프론트엔드 타입 검사는 통과, Playwright 테스트 전 통과, Python 문법·import 모두 정상.
- **경고 수준(정적 분석)의 ruff Finding은 다수 있으나 실행 오류가 아님.** 이 중 대부분은 f-string 인자 문자열로 인한 false positive.

## 1. Python 백엔드 — 실제 실행 검증

| 항목 | 결과 | 근거 |
| --- | --- | --- |
| 문법 검사(compileall) | OK(에러 없음) | 80개+ 파일 Python 3.13 성공 컴파일 |
| 실제 import(.venv) | OK | api_context·web_api·stockrl·rea·finrl·platform 등 전 모듈 로드 |
| FastAPI 서버 실행 | OK | `uvicorn web_api:app` → 7개 라우트 |
| GET /openapi.json | HTTP 200 (14ms) | 실제 응답 수신 |
| GET /docs | HTTP 200 | 실제 응답 수신 |
| 서버 로그 에러 | 없음 | error/traceback/exception 검색 결과 없음 |
| TypeScript typecheck | OK(exit 0) | `tsc --noEmit`, strict+noUnusedLocals+noUnusedParameters |
| Playwright api.spec | 5 passed | fetch 모킹 테스트 전 통과 |
| configs JSON | OK | instruments.json·provider_settings.json·rea.json·web_settings.json 유효 |

## 2. 정적 분석(ruff) — 경고 수준 Finding

| 코드 | 건수 | 성격 | 실제 실행 오류? |
| --- | --- | --- | --- |
| F401 unused import | 172 | 미사용 임포트 | 아님(경고) |
| F821 undefined name | 44 | 미정의 이름 | 대부분 NO(see 3) |
| F16 f-string | 9 | f-string 형식 | 아님(경고) |
| F722 forward annotation | 11 | 전방 annotation 문법 | 아님(경고) |
| F841 assigned but unused | 8 | 할당 후 미사용 | 아님(경고) |
| F811 redefinition | 2 | 재정의 | 아님(경고) |
| F4 | 11 | 기타 | 아님(경고) |

### 2.1 F821 = false positive 확인(예)

`backend/stockrl/finrl/policy_learning/handlers.py:231`
```python
def download(name: Literal["sac.zip", "dataset.json"],
              currency: Literal['KRW','USD']|None=None):
```
`KRW`/`USD`는 f-string 인자 문자열이므로 미정의 이름이 아님. 같은 이유로 `trading/operation_control/handlers.py:18`의 `feed/paper/engine/learning`, `connection_settings/handlers.py:23`의 `paper/real`도 문자열 라우트 경로라 미정의 이름이 아님.

### 2.2 실제 관심 Finding(경고이긴 하나 확인 권장)

- `backend/stockrl/finrl/policy_learning/handlers.py:52` F722 — `currency: Literal["USD","KRW"] = "USD"` 형태. forward annotation 문법 문제.
- `backend/stockrl/extensions/moe/handlers.py:93` F811 — `champion_structure_environment` 재정의(line 14).
- `backend/stockrl/finrl/policy_learning/official_cli.py:50` F841 — `model` 할당 후 미사용.
- `backend/stockrl/management/diagnostics_logs_code_apply/handlers.py:143` F841 — `official` 할당 후 미사용.
- `backend/stockrl/trading/operation_control/operations_runtime.py:455,492` F841 — `latest_rows`·`nav` 할당 후 미사용.
- `backend/stockrl/api_context.py` F401×30+ — 문서/설정용 임포트 모음.

## 3. 미완료

- ruff Finding 172건(unused import) + F821 44건(false positive 확인) + F16/F722/F841/F811 등은 경고 수준으로 유지. 실제 실행 오류로 분류하지 않음.
- Hermes 엔진(`backend/ai_agent/Hermes/`)은 제외(제3자 코드).
- `data/` 가격 DB 행 0개는 설계상(새 저장소 초기 상태). 시세 수신 전까지는 빈 저장소로 정상.

## 4. 검증 방법

- Python 문법: `python -m compileall <파일>`
- 실제 import: `.venv/Scripts/python.exe -c "import <모듈>"`
- 서버 실행: `.venv/Scripts/python.exe -m uvicorn web_api:app --host 127.0.0.1 --port 8791`
- 타입 검사: `../node_modules/.bin/tsc --noEmit` (frontend/에서)
- 테스트: `npx playwright test --project=api`
- 정적 분석: `ruff check backend/stockrl backend/web_api.py ...`
