# React 단일 프론트 통합 결과

최종 접속 주소: http://127.0.0.1:8766/

현재 FastAPI 하나가 React 정적 빌드와 기존 SAC API를 제공합니다. 5173은 Vite 개발 서버이며 API를 같은 8766 프로세스로 전달합니다. 운영 런처는 Vite를 시작하지 않습니다.

## 수정한 파일

| 파일 | 변경 내용 |
| --- | --- |
| `서버켜기.cmd` | 한 개의 통합 런처 호출. 자동 패키지 설치·별도 8767 API·Vite 운영 실행 제거 |
| `scripts/start_server.py` (추가) | 설치된 도구로 타입 검사·빌드. 서버 실제 cwd·명령행·생성 시각 확인, startup lock, 기존 8766 서버 재사용 |
| `src/stockrl/web_api.py` | React index/assets 제공, 8766 동일 출처 허용, 소유권 확인용 health 메타데이터. 기존 학습 API 로직 수정 없음 |
| `frontend/vite.config.ts` | 개발 proxy를 8767에서 8766으로 변경 |
| `frontend/start.cmd` | 개발 전용 유지. 자동 패키지 설치 제거 |
| `frontend/src/pages/ConnectionSettings.tsx` | API 표시 주소를 현재 접속 출처로 표시. 디자인·기능 유지 |
| `frontend/playwright.config.ts` | 테스트 기본 주소 8766. 개발 주소 별도 검증을 위한 환경 변수 |
| `frontend/tests/server-entrypoints.spec.ts` (추가) | 정적 React·assets, 개발 proxy와 동일 API PID, Origin/API 오류 경로 검사 |
| `README.md`, `frontend/README.md` | 운영 8766 / 개발 5173 실행 방법 명시 |
| `FRONTEND_INTEGRATION_AUDIT.md` (추가) | 실제 참조·중복·미참조 판단과 처리 근거 |
| `FRONTEND_INTEGRATION_RESULT.md` (추가) | 변경 파일·유지 파일·검증 결과 |
| `AGENTS.md` (추가), `.gitignore` | 추가 사용자 지시: 모든 삭제 대상을 폐기 전용 `휴지통/`으로 이동, 내부 접근·관리 금지, `/휴지통/` 업로드 차단 |

## 삭제 또는 비활성화한 파일

- 삭제한 파일: 없음. 휴지통으로 이동한 파일도 없음.
- `ui.py`, `expert_ui.py`: 기존 Streamlit 화면 소스는 남겨 두고, 직접 실행을 막는 안내만 추가.
- 확인한 이 프로젝트의 Streamlit 8766(PID 33332)과 이전 FastAPI 8767(PID 18628) 서버만 종료. 학습·Expert 자식 프로세스를 재귀 종료하지 않음.

휴지통 내부는 조회·수정·이동·삭제하지 않았습니다. 관리 기능·호환 코드·소스/import/설정/실행 경로 연결은 만들지 않았습니다.

## 유지한 파일

- `framework.py`, `official_cli.py`, `job_worker.py`, `expert_observation.py`, `expert_registry_native.py` 및 Frozen Expert 실행·입력 계약 모듈.
- FinRL-X 공식 Python 소스, 설치된 FinRL 및 Stable-Baselines3 공식 Python 소스.
- SAC 설정, Actor/Critic, Replay, Optimizer/Loss, 환경 보상·수수료·행동·관측 코드.
- `configs/`, 가격 DB, SAC 정책, Replay 파일, 체크포인트, Expert 결과 기록.
- 외부 Expert 패키지 35개.
- React App·Shell·흰색 테마·메뉴·나머지 페이지.
- `frontend/src`, `frontend/dist`, `.venv`, `node_modules`, `runtime`은 역할이 다르므로 삭제하지 않음.
- 공식 FinRL-X의 독립 Streamlit 예제와 console entrypoint는 원본 상태로 유지. 통합 실행 경로에서는 호출하지 않음.
- 현재 Frozen PPO Expert 호환 경로는 사용 중이므로 유지. 과거 중앙 PPO API는 현재 연결되지 않은 상태를 유지.
- `package.json`, `package-lock.json`, `requirements/operations.txt`의 작업 전후 해시 일치. 라이브러리 설치·업그레이드 없음.

## 실제 검증 결과

- 8766의 HTML은 `frontend/dist/index.html`을 제공하고 해당 JS/CSS assets는 HTTP 200.
- 8766에서 React 학습 화면과 현재 `finrlx-official-sac-v2` API 조회 성공.
- 5173은 `/src/main.tsx`를 제공하는 개발 서버. 그 `/api/health`는 8766과 동일 PID·project를 반환.
- 현재 리스너: 통합 8766 1개(PID 27164), 이전 8767 0개, 개발 5173 1개(PID 19016).
- 이 프로젝트의 Streamlit 프로세스 0개.
- 통합 실행 스크립트를 동시 재실행해도 동일 PID 27164를 재사용.
- 다른 프로젝트 cwd·명령행은 소유권으로 인정하지 않는 모의 프로세스 검증 통과. 실제 외부 프로세스를 종료한 시험은 하지 않음.
- TypeScript 검사·React 빌드 통과. Playwright 운영/개발/기존 화면 테스트 10개 통과.
- 보호 파일 227개의 SHA-256 작업 전후 일치. 여기에 핵심 프로젝트 Python 코드, 공식 프레임워크 Python 소스, 설정, 가격 DB, 저장 정책·Replay 등이 포함됨.
- 외부 Expert 패키지 35개의 파일 크기·수정 시각 일치. 대용량 패키지의 SHA-256을 재산출한 검증으로 보고하지 않음.
- 실제 학습·원격 수집·모델 교체는 검증 중 실행하지 않음.
- `git diff --check` 통과, Git HEAD `00efed29cbd119651659482c3a19641f49e07714` 유지.
- `/휴지통/` 무시 규칙은 `git check-ignore --no-index`로 확인. 휴지통 내 파일을 만들거나 조회하지 않음.

## 작업 전후 diff 제출

작업 시작 전부터 수정·삭제·미추적 파일이 있었습니다. 따라서 현재 HEAD 대비 diff 전체를 이번 요청의 변경으로 표시하지 않습니다.

- [작업 시작 전 git diff](runtime/frontend-integration-audit/before-git.diff)
- [작업 종료 후 git diff](runtime/frontend-integration-audit/after-git.diff)
- [이번 요청의 파일 스냅샷 비교 diff](runtime/frontend-integration-audit/changes-this-request.diff): 추적·미추적 파일을 모두 포함.
- [보호 파일 검증·변경 파일 목록](runtime/frontend-integration-audit/verification.json)
- [프로세스 소유권·최종 포트 기록](runtime/frontend-integration-audit/processes-after.json)
- [파일별 실제 참조 목록](runtime/frontend-integration-audit/references.json)

기존 삭제 표시가 있던 `.gitmodules`, `SETTINGS.md`, `pyproject.toml`, `설치.cmd`는 이번 작업에서 삭제하거나 복원하지 않았습니다.
