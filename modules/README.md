# 조립식 모듈

용도: 모듈 등록·소스/패키지/데이터 소유·탈착과 독립 배포의 현재 완료 범위를 안내합니다.

`modules/<id>/module.json`과 그 안의 backend/frontend를 하나의 프로그램 단위로 취급합니다. 중앙 등록 파일에 기능별 import나 메뉴를 추가하지 않습니다.

- `schema: 1`, 고유 `id`, `group: {id,title}`, 선택 `order`를 선언합니다.
- `backend: {namespace, entry, path?}`: 기본 path는 backend. entry가 MENU+router 또는 GROUP+ROUTERS를 제공합니다. 선택 hooks는 busy_reason/reserve_restart/cancel_restart/close입니다. register_host(app)은 프로젝트 정적 화면 제공처럼 공통 호스트 연결이 필요할 때만 사용하며 기능 API는 기존 단일 /api로 등록합니다.
- `frontend: {entry: "frontend/register.ts"}`: menus와 선택 registeredMenus(actions)를 export합니다. React/Vite/Tailwind 및 `@platform/ui` 공통 컴포넌트를 사용합니다.
- 외부 설치기의 `install_revision`이 있는 앱은 GitHub 대메뉴 아래 앱별 중메뉴로 취합합니다. 선택 `app_title`은 중메뉴 이름이며 이전 설치본은 기존 group 제목을 사용합니다. 프론트/백엔드 공통 등록 시 적용하므로 기존 소스·데이터·주소를 옮기거나 생성 파일을 수동 수정하지 않습니다. 플랫폼 포함 AI 에이전트/Hermes/MCP는 이 규칙의 대상이 아닙니다.
- `data`: 프로그램 밖의 영속 경로. `resources`: 기존 실행 환경·공통 실행기 경로. 모듈 탈착은 이 경로를 이동·삭제하지 않습니다.

공통 감시기가 등록 정보 변경을 감지해 실행 중 작업을 확인하고, import 사전 확인·타입 검사·빌드·서버 적용을 처리합니다. 작업 중에는 적용을 보류합니다. 설치 실패는 runtime/platform 로그에 남기며 사전 확인 실패 시 기존 서버를 종료하지 않습니다.

Hermes 코드는 hermes/backend와 hermes/frontend에 들어 있습니다. 원래 외부 Hermes 폴더는 사용하지 않습니다. Python 환경은 modules/hermes/.venv, DB·기록·설정은 runtime/ai_agent/Hermes, 모델 실행기는 runtime/shared를 재사용합니다.

금융과 REA의 실제 backend/frontend 소스는 각 modules/finance·modules/rea에 있습니다. 각 Python 가상환경, Node 패키지, 의존성 명세와 설정을 모듈 내부에 소유합니다. 이전 backend/stockrl·backend/rea에는 import 호환 연결만 남습니다. frontend/src/pages/finance·rea는 이동 안내 문서만 남겨, 모듈 폴더가 없어도 빌드가 중단되지 않습니다. 업무 구현을 두 곳에서 유지하지 않습니다. 호스트는 공통 UI/등록 규격과 IPC만 제공하고 업무 라이브러리를 import하지 않습니다.

오버로드 → 나자릭은 [등록·화면](nazarick/README.md)과 [실제 백엔드](../backend/overlord/nazarick/README.md)를 연결합니다. 백엔드 중메뉴·소메뉴 소스는 `backend/overlord/nazarick/`, 데이터는 `runtime/overlord/nazarick/`이며 자동 등록 폴더에는 등록 연결과 화면만 둡니다.

AI 에이전트의 공식 원본 등록·화면은 [Hermes 원본](hermes_original/README.md)과 [OpenClaw 원본](openclaw_original/README.md), 실제 중메뉴 구현은 `backend/ai_agent/`가 소유합니다. 원본 체크아웃은 `.gitmodules`의 고정 커밋, 한국어 변경은 추적되는 패치로 보존하며 사용자 상태·도구와 구분합니다.

## 최종 목표와 현재 경계

외부 저장소의 최초 구조 분석·변환도 플랫폼이 수행해야 합니다. 사용자가 직접 어댑터를 만드는 것을 최종 사용 흐름으로 삼지 않습니다. 기존 화면·공식 실행기를 우선 재사용하고, 변환한 프로그램의 실행을 확인한 뒤 등록합니다. 실패한 변환은 이유를 표시하며 성공으로 등록하지 않습니다.

등록된 프로젝트는 메뉴 이동과 기능 호출로 연결되고, Hermes는 허용된 작업 범위 안에서 다른 프로젝트의 소스를 수정·검증할 수 있어야 합니다. 분리 배포에는 필요한 공통 코드·의존성을 포함하고 플랫폼이 없는 환경에서 실행 확인이 필요합니다. 모듈 폴더 분리만으로 독립 배포를 검증했다고 보고하지 않습니다. Expert 선택·조합·분리도 같은 소유권·의존성 확인 원칙을 따릅니다.

현재 구현은 등록 규격, 자동 메뉴/API 연결, 작업 보호, 자동 빌드·적용과 금융·REA·Hermes의 실제 소스/패키지 분리 및 폴더 탈착입니다. [프로젝트 설치·관리](projects/README.md)는 공개 GitHub 검색·주소 등록, 지원 실행 구조의 자동 어댑터, 기존 Hermes를 통한 추가 변환 요청, 원본 UI 실행 확인·설정·업데이트·분리를 제공합니다. 임의의 모든 저장소가 자동 변환된다고 보장하지 않습니다. 기본 금융·REA·Hermes의 독립 실행 소스 ZIP은 프로젝트 관리의 내보내기에서 제공합니다. 프로젝트 간 공통 협업 도구와 Expert 공통 규격은 후속 구현 대상입니다.


## 모듈 실행 규격과 환경 소유

`runtime`은 `{language, protocol:"module-jsonl-v1", command:[...], state, package?, entry?}`를 선언합니다. command는 shell 문자열이 아니며 모듈 폴더를 cwd로 사용하고 `{module}`을 실제 폴더로 치환합니다. Python은 모듈 `.venv`를, Node는 자체 코드·node_modules를 사용합니다. 표준 입력/출력의 `id,operation,payload` / `id,result|error`로 describe·request·hook·shutdown을 교환합니다. 원본 엔진에는 해당 언어의 얇은 어댑터가 필요하며 Node 업무 코드를 Python으로 번역하지 않습니다. 공식 OpenClaw 원본 설치·Gateway 연결은 전용 중메뉴가 담당하며 범용 Node JSONL 변환과 구분합니다.

금융·REA의 worker.py는 자신의 API와 상태만 제공하며 추가 HTTP 포트가 없습니다. 호스트 module_runtime.py가 단일 `/api`에 연결하고 원본 입력 스키마·상태 코드·응답을 유지합니다. 모듈 하나의 의존성 로딩이 실패하면 오류를 표시하고 나머지 호스트/모듈을 유지합니다. 재시작은 전체 busy 확인 → 예약 → 전용 실행기 종료 → 적용 순서이며 실패 시 성공으로 표시하지 않습니다.

실제 설치 위치: 호스트 `.venv/platform`, 금융 `modules/finance/.venv`와 내부 kiwoom, REA `modules/rea/.venv`·node_modules, Hermes `modules/hermes/.venv`·backend/engine/browser/node_modules. 이전 루트 `.venv`는 개발 검사·복구용으로 남아 있고 운영 API는 사용하지 않습니다. 가상환경/실제 설치 패키지·개인 설정은 Git 제외, 모듈 소스·명세·잠금만 추적합니다. 모듈 Python의 소스 훅은 모듈 위치를 동적으로 찾아 기존 host/backend 이름에 의존하지 않습니다.

데이터/모델은 이동하지 않았습니다. 기존 runtime/<소유 메뉴>·금융 가격 DB·외부 모델을 module.json의 data/resources 소유 정보로 연결합니다. 플랫폼 UI 렌더링 계약과 외부 Python/Node/CUDA 실행 환경까지 제거한 다른 PC용 완성 포터블 배포를 검증한 것은 아닙니다.

## 환경 분리 확인 — 2026-10-18

- 실제 금융·REA·Hermes 폴더와 전용 패키지 환경을 임시 위치로 옮긴 동안 호스트/GitHub 메뉴·API·브라우저가 정상 동작했습니다. 그 위치에서 금융 32개 API, REA 8개 API와 Node SDK 170개 도구, Hermes 임시 홈 상태 조회를 확인했습니다. 복원 후 네 모듈 모두 사용 가능하며 중앙 등록 소스 수정은 0건입니다. 기록: `runtime/platform/module-verification/builtin-isolation.json`. 데이터·모델 파일은 이동하지 않았습니다.
- 로컬 관련 회귀 59개·Node 메뉴 검사 3개·프론트 API 검사 5개·TypeScript·Vite 빌드 통과. Node 실행기 계약·UTF-8 통신, 의존성 실패 격리, 비업무 호스트 기동, 큰 파일/Range, 가상환경 이동 후 console 실행기 복구, 모의 금융/REA 요청을 포함합니다. 전용 Python 환경 다섯 개의 pip check가 통과했습니다. 전체 테스트나 GitHub CI가 통과했다는 뜻은 아닙니다.
- 검사 중 기존 모의 객체가 프로세스 경계를 넘지 못해 실제 금융 시작 요청 1건이 Expert 적재 단계까지 진행된 실수가 있었습니다. 해당 프로세스는 종료됐고 그 검사 작업만 취소 표시했습니다. 기록상 학습·매매 단계는 pending이었으며 해당 요청의 성공 체결은 확인되지 않았습니다. 이후 유효한 쓰기 요청 검사는 임시 데이터와 같은 프로세스의 모듈 라우터로 분리해 재실행했습니다. 근거: `runtime/platform/module-verification/interrupted-request-test.json`.
- 운영 서버는 `.venv/platform`으로 적용했고 네 모듈 available·실행 차단 작업 없음·금융/REA/Hermes 세 화면 연결·JavaScript 오류 0건을 확인했습니다. GitHub CI 결과는 아직 미확인입니다.
- 실제 시세·학습·추론·가상체결 전체 회귀, 다른 PC 독립 배포, OpenClaw 원본 설치/어댑터는 이번 변경의 검증 완료 항목이 아닙니다.

추가 점검(2026-10-18): 공통 실행기의 재시작 예약 확인 중 새 요청이 들어가는 경쟁 조건과 종료 요청이 죽은 실행기를 다시 시작하는 경로를 재현·수정했습니다. 등록/폴더 탈착 검사 6개와 런타임 검사 8개가 통과했습니다. 실제 Node 예약·취소·기존 프로세스 재사용·종료도 포함합니다. 금융·REA·Hermes는 운영 API 조회에서 available을 확인했습니다. 이번에는 실제 사용자 폴더를 다시 이동하거나 사용자 모델 추론을 실행하지 않았으며, 이전의 폴더 이동 확인과 이번 회귀 검사를 구분합니다. 이 점검 당시에는 기본 모듈 독립 배포가 미완료였습니다. 현재 소스 ZIP 내보내기/단독 실행은 아래 독립 실행 소스 항목을 따르며 다른 PC 새 설치 재현은 미확인입니다. 구현·검사 연결은 [호스트 안내](../backend/README.md)를 따릅니다.

## 기본 모듈 독립 실행 소스

GitHub → 프로젝트 관리 → 설치된 프로젝트에서 금융·REA·Hermes 각각 설치 정보 → 개발자 상세에서 전달용 **소스 ZIP 복사본 저장**을 선택할 수 있습니다. 선택 모듈, 필요한 공통 API/React/Vite/Tailwind 코드의 복사본, 설치 명세와 setup/check/run 진입점을 함께 묶습니다. 독립 배포본은 공통 코드를 원래 플랫폼에서 import하지 않고 자신의 복사본을 소유합니다. 실행에 원래 플랫폼·다른 업무 모듈·Codex는 필요하지 않습니다. 실제 패키지는 setup이 배포 폴더 안에 설치하며 Python/Node/Git 등 시스템 실행기는 별도 전제입니다. 데이터/키/원본 모델은 자동 복사하지 않습니다. 같은 PC의 독립 실행 검사와 다른 PC 신규 설치/전체 업무 실행은 구분합니다. 현재 조건·검사 자료는 [프로젝트 관리](projects/README.md)를 봅니다.

현재 로컬 분리/재연결은 프로젝트 관리의 분리 버튼으로 자동 처리합니다. 기본 모듈의 실제 프로그램/전용 환경과 소유 data를 standalone 폴더로 옮기고 독립 호스트/UI와 현재 설치 의존성을 준비합니다. 복귀 시 같은 파일을 원래 위치에 되돌립니다. 데이터가 빠진 전달용 ZIP과 사용자 설정/데이터를 보존하는 로컬 분리를 구분합니다. 자세한 흐름과 확인 범위는 프로젝트 관리 README를 따릅니다.
