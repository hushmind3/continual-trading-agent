# 프론트 통합 사전 조사

기준: 현재 작업 트리. 이번 작업 이전에도 수정·삭제·미추적 파일이 존재했습니다. Git HEAD 기준 차이와 이번 요청의 추가 차이는 별도로 기록합니다.

## 실제 실행 경로

| 경로 | 실제 참조·역할 | 조사 결과 / 처리 |
| --- | --- | --- |
| `서버켜기.cmd` | uvicorn `stockrl.web_api:app` 8767 + Vite 5173 | 운영 실행인데 두 서버를 시작하고 중복 확인이 없음. 8766 통합 실행으로 변경 |
| `ui.py` | Streamlit 화면 → `framework.sac_example`, `official_cli` 자식 프로세스 → `framework.train/backtest`; `exec(expert_ui.py)` | React와 같은 기능의 별도 프론트. 원문 보존 후 직접 실행 비활성화 |
| `expert_ui.py` | Streamlit 위젯 → `ExpertRegistry.catalog/select/register` | `ui.py`의 화면 부품. React가 동일 Registry에 연결되어 있음. 원문 보존 후 실행 비활성화 |
| `frontend/src/main.tsx → App.tsx → Shell.tsx → pages/*` | React 상단 7개 메뉴 / TypeScript 화면 | 유일한 활성 프론트로 유지 |
| `frontend/src/data/api.ts` | 동일 출처 `/api/*` 호출 | 운영에서는 8766, 개발에서는 Vite proxy를 거쳐 8766 |
| `src/stockrl/web_api.py` | 기존 서비스에 연결하는 FastAPI API | 유일한 프로젝트 HTTP API로 유지. React dist 정적 제공만 추가 |
| `src/stockrl/job_worker.py` | HTTP 작업 기록 / 원본 CLI 또는 공식 데이터 수집 호출 | API와 중복된 학습기가 아님. 유지 |
| `src/stockrl/__main__.py → official_cli.py → framework.py` | 터미널 학습·백테스트·Expert 목록 | HTTP 진입점과 역할이 다름. 현재 SAC CLI 유지 |
| `frontend/start.cmd` | Vite 개발 서버 | 통합 운영 서버와 역할이 다름. 개발 전용으로 유지 |
| `scripts/install_windows.py` | 설치 절차 | 실행 서버가 아님. 변경하지 않음 |

## 모듈별 중복·미참조 판단

| 파일 / 영역 | 확인된 참조 | 판단 |
| --- | --- | --- |
| `expert_registry_native.py` | framework의 학습·관측 경로, CLI, HTTP, Streamlit | 실제 Frozen Expert Registry. 유지 |
| `expert_registry.py` | `expert_backends.run_native.publish`의 타임스탬프·JSON 호환 함수 | 이름이 비슷하지만 Registry 구현과 중복 아님. 유지 |
| `state_io.py` | Registry·작업·API·자원 적재 등 | 공통 저장 유틸. 유지 |
| `moe_native.py`, `expert_backends.py`, `moe_stock_policies.py`, `expert_device.py` | `ExpertPool → NativeExpert/native_call/StockPolicyExpert` | Frozen 모델 실행기. 구형 중앙 PPO 학습기로 분류하면 안 됨. 유지 |
| `platform/assets.py → expert_residency/resources/observations/expert_packages/expert_contracts` | Registry 추론·원본 패키지 실행 | 현재 Expert 입출력·적재 경로. 유지 |
| `platform/quantized_linear.py`, `nf4_linear.py`, `hf_forecast.py`, `gguf_expert.py`, `llama_engine.py` | Expert 적재 분기·원본 커널·GGUF 실행 | 실제 사용되는 실행 부품. 유지 |
| `paths.py` | `expert_backends.expert_weight_path` | 사용 중 경로 유틸. 유지 |
| `platform/package_disposal.py` | 현재 소스에서 호출 참조 미발견 | 삭제 후보일 수 있으나 외부 패키지·동적 참조를 단정할 수 없음. 이번 범위에서 유지 |
| `framework.finrl_file` | 현재 정적 호출 참조 미발견 | 미참조 헬퍼. 학습 코드 영역이므로 변경하지 않음 |
| `frontend/src/ui/format.ts` 일부 export | `inferenceChange/calendarDate/inspectionDetail/workerState` 호출 미발견 | 구형 화면의 보조 함수 잔재. 통합과 무관하므로 유지 |
| `frontend/src/data/library.ts` | `expertFamilies.ts`의 type import | 동일 Expert 타입의 별칭. 중복 API 아님 |
| PPO 문자열·정책 분기 | `moe_stock_policies`, `expert_contracts`의 Frozen A2C/PPO/SAC 패키지 계약 | 현재 Expert 호환 기능. 삭제·변경하지 않음 |
| 과거 `controls/*`, `library/*`, `policies/rollback` | 현재 React 실제 호출 없음 | 과거 PPO/Champion 운영 API가 복원되어 있지 않음 |

## 분리된 폴더와 공식 원본

- `frontend/src`: 편집 소스. `frontend/dist`: 빌드 산출물. 중복 아님.
- `.venv`, `node_modules`: Python/JavaScript 런타임 의존성. 중복 프론트 아님.
- `runtime`: 정책·Replay·로그·작업·이전 프론트 보관 기록. 삭제하지 않음.
- `data`, `configs`, 외부 `Desktop/모델`: 데이터·설정·Expert 원본. 보존.
- `FinRL-X/src/web/app.py`, `src/main.py`, `tools/dashboard.py` 및 공식 console entrypoint: 공식 서브모듈의 독립 예제·CLI. 프로젝트 통합 런처가 호출하지 않음. 원본이므로 비활성화 수정조차 하지 않음.
- 과거 `web_app.py`, `launch_web.py`, `platform/api.py`는 현재 작업 트리에 없음. `f153957`의 정적 파일 제공 패턴만 참고하고 PPO 백엔드는 가져오지 않음.

## 확인된 프로세스

사전 조사에서 8766은 이 프로젝트의 `streamlit run .../ui.py`, 8767은 이 프로젝트 cwd의 `uvicorn stockrl.web_api:app`, 5173은 이 프로젝트 `frontend/node_modules/vite/bin/vite.js`였습니다.
PID는 재사용될 수 있으므로 중지 전 실행 경로·cwd·생성 시각을 다시 확인합니다. 학습·Expert 작업이나 다른 프로젝트 서버는 중지하지 않습니다.

참조 목록·작업 시작 전 diff·보호 파일 해시: `runtime/frontend-integration-audit/`.

## 내용이 같은 파일 조사

프로젝트 소유의 Python·React·실행 스크립트 전체 파일을 SHA-256으로 비교한 결과 내용이 완전히 같은 파일은 0개였습니다. 역할이 겹치는 부분은 Streamlit/React 프론트와 운영 런처의 분리 서버 실행이며, 공통 Registry와 작업 CLI는 중복 구현으로 판정하지 않았습니다. 공식 패키지의 빈 `__init__.py` 등 패키지 표시 파일도 합치지 않습니다.

## 통합 후 실행 경로

`서버켜기.cmd → scripts/start_server.py → 설치된 tsc/Vite build → uvicorn stockrl.web_api:app:8766`.

- `GET /`는 기존 React `dist/index.html`, `/assets/*`는 해당 빌드의 정적 파일을 제공합니다.
- React의 동일 출처 `/api/*`는 기존 SAC API 함수에 연결됩니다.
- Vite 5173은 개발 전용이며 동일한 8766 API로 전달합니다. 운영 런처에서 Vite를 실행하지 않습니다.
- 재실행은 startup lock과 포트 프로세스의 실제 cwd·명령행·생성 시각을 확인합니다. 다른 프로젝트 프로세스는 종료하지 않습니다.
- 확인된 이 프로젝트의 Streamlit 8766과 이전 FastAPI 8767 서버만 종료했습니다. 학습·Expert 자식 프로세스를 재귀 종료하지 않습니다.
- `ui.py`, `expert_ui.py`는 직접 실행을 막는 안내만 추가했고 기존 원문은 남겼습니다. 삭제된 파일은 없습니다.

운영 주소의 정적 React 화면, 개발 주소의 화면과 동일 backend PID, Origin 처리, 기존 7개 화면의 조회·오류 경로를 포함한 Playwright 10개 테스트가 통과했습니다. 실제 학습·원격 수집·모델 교체는 실행하지 않았습니다.

작업 전후 파일별 diff·프로세스·해시 검증 상세는 `runtime/frontend-integration-audit/`의 결과를 함께 확인하세요. 기존에 삭제 표시가 있던 `.gitmodules`, `SETTINGS.md`, `pyproject.toml`, `설치.cmd`는 이번 요청에서 삭제하거나 복원하지 않았습니다.
