# 프로젝트 플랫폼

용도: 현재 로컬에서 사용하는 모듈형 프로젝트 플랫폼의 소스·메뉴 계층·설치·실행과 GitHub 복원 경계를 안내합니다. React + Vite + Tailwind 프론트엔드와 FastAPI 단일 `/api`를 사용합니다.

작업·배포 기준 브랜치는 **`main`**입니다. 이 저장소는 금융 전용 프로젝트에서 금융·REA·AI 에이전트·오버로드·프로젝트 관리를 포함하는 플랫폼으로 확장됐습니다.

## 메뉴와 실제 소스

| 대메뉴 / 중메뉴 | 담당 기능 | 실제 구현·안내 |
| --- | --- | --- |
| 금융 | 운영 제어·가상계좌·주문·학습·MoE·연결 | [금융 모듈](modules/finance/README.md) |
| REA 역공학 | 프로그램 분석·프로젝트 탐색 | [REA 모듈](modules/rea/README.md) |
| AI 에이전트 / 헤르메스 | 기존 이식 엔진·대화·모델·작업 환경·MCP·스킬 | [이식 Hermes](modules/hermes/README.md) |
| AI 에이전트 / 헤르메스 원본 | 공식 원본 실행·한국어 대시보드 | [실제 백엔드](modules/ai_agent/HermesOriginal/backend/README.md) · [등록·화면](modules/ai_agent/HermesOriginal/README.md) |
| AI 에이전트 / OpenClaw 원본 | 공식 Gateway·Control UI·실행 제어 | [실제 백엔드](modules/ai_agent/OpenClawOriginal/backend/README.md) · [등록·화면](modules/ai_agent/OpenClawOriginal/README.md) |
| 오버로드 / 나자릭 | 연결 대상·어댑터 규격·등록 확인·기록 | [나자릭](backend/overlord/nazarick/README.md) |
| GitHub / 프로젝트 관리 | 검색·설치·실행·분리·재연결·소스 배포 | [프로젝트 관리](modules/projects/README.md) |

중메뉴가 있는 기능은 **소메뉴 → 중메뉴 매니저 → 대메뉴 매니저 → 전체 메뉴 총괄 → 단일 `/api`**로 연결합니다. 자동 등록은 기존 `modules/<id>/module.json`과 중메뉴 소유형 `modules/<대메뉴>/<중메뉴>/module.json`을 함께 지원합니다. 등록용 연결 파일에는 업무 코드를 복제하지 않습니다.

## 디렉터리 역할

| 위치 | 역할 |
| --- | --- |
| [backend/](backend/README.md) | 전체 메뉴 총괄·단일 API·공통 호스트. 대메뉴 공통 등록·오버로드 중메뉴 구현 포함 |
| [modules/](modules/README.md) | 모듈 등록 정보·화면·기존 모듈 소유 구현·전용 설치 환경 명세 |
| [frontend/](frontend/README.md) | React/Vite 호스트·공통 UI·Tailwind 테마·자동 메뉴 등록 |
| [development/](development/README.md) | 설치·서버 적용·필요한 검사 소스와 개발 안내 |
| `runtime/<대메뉴>/<담당 메뉴>/` | 사용자 설정·대화·DB·작업·설치한 원본 앱의 실행 자료. 아래 공식 원본 Git 의존성 두 경로 외에는 Git에서 제외 |
| `runtime/platform/`, `runtime/shared/engines/` | 서버 실행·적용·감시 / 실제 공유 실행기 |
| `data/`, `모델/`, `휴지통/`, `.worktrees/` | 사용자 데이터 / 지정 모델 / 폐기 파일 / 별도 작업 체크아웃. Git 배포 제외 |

기존 금융·REA·이식 Hermes는 각 모듈이 소스와 전용 패키지를 소유합니다. 원본 AI 연결은 `modules/ai_agent/<중메뉴>/` 안에 backend·frontend·패치·등록 정보를 함께 소유합니다. 나자릭의 실제 백엔드는 `backend/overlord/nazarick/`이며 등록·화면은 해당 모듈이 소유합니다.

시장조사·사업 검토 등 실행 코드에서 사용하지 않는 결과물은 소스 배포에서 제외합니다. 새 결과물은 담당 메뉴의 `runtime/` 아래에 보관하고, 기존 루트 `research/` 자료는 로컬 `휴지통/research/`에 원래 상대 경로대로 보존했습니다. 루트 `research/`와 휴지통은 Git 추적 대상에서 제외합니다.

## GitHub에서 소스 받기

```sh
git clone --recurse-submodules https://github.com/hushmind3/continual-trading-agent.git project-platform
cd project-platform
```

이미 받은 저장소에 공식 원본이 빠졌다면 프로젝트 루트에서 실행합니다.

```sh
git submodule update --init
```

[.gitmodules](.gitmodules)에 기존 로컬 설치본과 같은 공식 원본 커밋을 고정합니다. 큰 원본 저장소를 복사해 중복 업로드하지 않고, GitHub에서 출처와 정확한 버전을 따라갈 수 있습니다.

| 원본 | 고정 커밋 | 체크아웃 경로 | 로컬 수정 |
| --- | --- | --- | --- |
| [OpenClaw](https://github.com/openclaw/openclaw/tree/99599dbf83d67b5feb27df2ffcc22ae0f18f00d1) | `99599dbf83d67b5feb27df2ffcc22ae0f18f00d1` | `runtime/ai_agent/OpenClawOriginal/source/` | 프레임·접근 제어는 플랫폼 연결 코드가 담당 |
| [Hermes](https://github.com/NousResearch/hermes-agent/tree/bf0203a794a07aac3ff764972ab9087baa4e4f4e) | `bf0203a794a07aac3ff764972ab9087baa4e4f4e` | `runtime/ai_agent/HermesOriginal/source/` | [한국어 화면 패치](modules/ai_agent/HermesOriginal/korean-ui.patch) |

Git 복원은 소스 복원입니다. Python/Node 패키지·원본 PM 도구·모델·계정·사용자 데이터는 설치 또는 별도 준비가 필요합니다. 원본별 준비 방법과 실행 경계는 위 실제 백엔드 README를 따릅니다.

Hermes 한국어 패치의 현재 적용 상태·보관 위치·복원 절차는 [담당 메뉴의 기준 안내](modules/ai_agent/HermesOriginal/README.md#한국어-패치)에서 관리합니다. [별도 보관 폴더](modules/ai_agent/HermesOriginal/patches/2026-10-24_한국어패치/)도 이 안내에서 연결합니다.

## 설치와 실행

- macOS: `설치.command` → `서버켜기.command`.
- Windows: `설치.cmd` → `서버켜기.cmd`.
- 기본 주소: `http://127.0.0.1:8766/`.
- 세부 준비·실행 중 작업 보호: [실행 안내](development/scripts/README.md).

운영 호스트는 `.venv/platform/`, 금융은 `modules/finance/.venv/`, 키움은 `modules/finance/.venv/kiwoom/`, REA는 `modules/rea/.venv/`, 이식 Hermes는 `modules/hermes/.venv/`를 사용합니다. 각 모듈이 자신의 의존성 명세·설정을 소유합니다. npm 루트 workspace는 플랫폼 프론트엔드용이며 REA·이식 Hermes 브라우저 패키지와 원본 앱 환경은 각 소유 경로에서 관리합니다.

모델은 사용자가 지정한 원본 폴더에 유지하며 현재 Mac은 `모델/`을 사용합니다. 가격 DB는 `data/market_prices.sqlite3`, 이식 Hermes의 기존 대화·설정은 `runtime/ai_agent/Hermes/`입니다. 원본 Hermes와 OpenClaw의 `home/`, 인증·비밀번호·원격 접속 설정은 Git에 올리지 않습니다. 원격 접근 방법과 확인 범위는 [OpenClaw 안내](modules/ai_agent/OpenClawOriginal/README.md)를 따릅니다.

## 확인 범위

기능별 현재 구현·실제 확인·미완료 사항은 각 메뉴 README가 기준입니다. Mac의 플랫폼·이식 Hermes·원본 대시보드 연결과 나자릭의 대상 저장·등록 확인 경로를 확인한 기록이 있습니다. 금융 시세·학습·주문 전체, 원본 앱의 전체 외부 연동·모델 응답, 다른 PC의 신규 설치까지 완료했다는 의미는 아닙니다.

2026-10-24 정리: 원본 AI의 backend·frontend·패치·등록 정보를 각 `modules/ai_agent/<중메뉴>/` 한 폴더로 통합하고 두 공식 원본을 고정 Git 의존성으로 등록했습니다. 작업용 worktree 9개는 미반영 파일·고유 커밋을 보존해 `휴지통/.worktrees/`로 이동했으며 `main`에 합치거나 GitHub에 올리지 않았습니다. 원본 두 대시보드의 ready·HTTP 200과 Hermes Gateway 복구를 확인했습니다.

GitHub 정리에서는 기존 설치본과 데이터 경로를 유지합니다. 불필요한 재다운로드·재설치·모델 호출로 확인하지 않습니다. 로컬의 현재 소스와 원본 버전·패치·문서가 GitHub에서 재구성되는지 확인합니다. 개발 지침은 [AGENTS.md](AGENTS.md)를 따릅니다.
