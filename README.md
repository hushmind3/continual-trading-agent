# 프로젝트 플랫폼

용도: 현재 실행 구조·소스 소유·설치 진입점을 안내합니다. 대메뉴는 금융·REA 역공학·AI 에이전트·GitHub입니다.

| 위치 | 담당 |
| --- | --- |
| [modules/](modules/README.md) | 금융·REA·Hermes·프로젝트 관리의 실제 backend/frontend와 모듈 등록 정보 |
| [backend/](backend/README.md) | 전체 메뉴 취합·단일 `/api`·언어별 전용 실행기 IPC |
| [frontend/](frontend/README.md) | React/Vite/Tailwind 호스트·공통 UI·자동 메뉴 등록 |
| [development/](development/README.md) | 설치·실행·검사 스크립트와 조사 문서 |
| [금융](modules/finance/README.md) | 금융 소스·패키지·설정; [FinRL](modules/finance/backend/finrl/README.md) |
| [REA](modules/rea/README.md) | 프로그램 분석·프로젝트 탐색; 외부 설치 앱 morluto/rea와 별개 |
| [Hermes](modules/hermes/README.md) | 이식 엔진·대화·모델·작업 환경·MCP·스킬·프롬프트 |
| [GitHub 프로젝트 관리](modules/projects/README.md) | 검색·설치·실행·분리·재연결·제거·지원 앱 ZIP 내보내기 |

Mac 실행: **서버켜기.command**, 설치: **설치.command**. Windows 실행: **서버켜기.cmd**, 설치: **설치.cmd**. 세부 명령과 작업 보호는 [실행 안내](development/scripts/README.md)를 따릅니다.

운영 호스트는 `.venv/platform/`, 금융은 `modules/finance/.venv/`, 키움은 `modules/finance/.venv/kiwoom/`, REA는 `modules/rea/.venv/`, Hermes는 `modules/hermes/.venv/`를 사용합니다. 이전 루트 `.venv/`는 개발 검사·복구용이며 운영 업무 패키지의 공통 설치 위치가 아닙니다. 각 모듈의 의존성 명세·설정은 해당 모듈이 소유합니다.

npm 루트 workspace는 플랫폼 frontend만 관리합니다. REA의 Node 패키지는 `modules/rea/`, Hermes 브라우저 패키지는 `modules/hermes/backend/engine/browser/`에서 각 잠금 파일과 node_modules를 사용합니다.

데이터는 프로그램과 분리합니다. 가격 DB는 `data/market_prices.sqlite3`, REA 저장 프로젝트는 `runtime/rea/project_explorer/projects/`, Hermes 설정·대화는 `runtime/ai_agent/Hermes/`입니다. 서버·감시는 `runtime/platform/`, 공유 실행기는 `runtime/shared/engines/`에 둡니다. 모델 원본은 사용자가 지정한 폴더에 유지합니다. 현재 Mac에서는 프로젝트 `모델/`을 사용합니다. 금융 설정은 `modules/finance/configs/`, REA 설정은 `modules/rea/configs/`에 있습니다. 비밀 설정·실제 패키지·실행 기록·휴지통은 Git 배포 대상이 아닙니다.

메뉴·API는 `modules/<id>/module.json`에서 자동 등록하며 중앙 코드에 기능별 import를 추가하지 않습니다. 지원 Node 백엔드는 동일 IPC 규격으로 연결할 수 있지만 OpenClaw 원본 설치·어댑터는 아직 수행하지 않았습니다.

현재는 금융·REA·Hermes의 소스·패키지 분리와 플랫폼 안에서의 폴더 탈착을 확인했습니다. 금융·REA·Hermes는 프로젝트 관리의 독립 실행 소스 내보내기로 필요한 공통 코드 복사본과 설치/실행 진입점을 묶을 수 있습니다. 원래 플랫폼 경로 없이 선택 모듈만 실행하는 소스 배포이며, 시스템 Python/Node/Git·외부 모델/인증은 별도 전제입니다. 다른 PC 신규 설치와 전체 업무 실행은 미확인입니다. 외부 앱의 지원 형식 ZIP과 기본 모듈의 소스 배포 ZIP은 형식이 다릅니다. 현재 검증과 남은 작업의 기준은 [모듈 안내](modules/README.md), 기능별 결과는 각 소메뉴 README입니다. 조사·검사 문서의 과거 결과는 해당 날짜와 조건에만 적용합니다.

## macOS에서 이어서 실행
담당: Windows에서 옮긴 기존 플랫폼·Hermes·회사 데이터를 Mac에서 사용하는 진입점입니다. `서버켜기.command`를 더블클릭하면 기존 단일 API와 Hermes 화면을 엽니다. 최초 의존성 준비는 `설치.command`이며 Python 3.14·uv·Node.js·Homebrew가 필요합니다. 기존 install_windows.py가 운영체제에 맞춰 환경을 준비하므로 별도 하네스·DB를 만들지 않습니다.

Mac의 모델은 사용자 지정 프로젝트 `모델/`에 있으며 원본 GGUF를 그대로 사용합니다. Windows Python 실행파일·wheel·CUDA 바이너리는 Mac용으로 다시 준비해야 합니다. 설정의 옛 절대경로는 실제 Mac 경로로 옮겼고 원본 제어 설정은 runtime/platform/migration-backup에 보존했습니다. 대화·회사 DB의 과거 기록은 삭제하거나 새 DB로 바꾸지 않았습니다.

2026-10-21 실제 확인: Mac의 8766 React·단일 API, 기존 Hermes 대화 조회, 회사/회의 탭 표시, Ornith 9B의 Apple M5 GPU 적재(65,536 문맥·Thinking on), 기존 총괄 세션의 실제 응답 완료. 금융 CUDA·키움 환경은 Mac에 설치하지 않았으며 시세·학습·주문, 직원 회의/제품 제작 전체, GUI 컴퓨터 조작은 이번 이전에서 확인하지 않았습니다. 금융 모델 파일은 보존돼 있지만 해당 기능까지 Mac 동작 완료로 표시하지 않습니다.

2026-10-22 Mac 실행 경로 정리: 공통 native 실행기 탐색을 서버·설치·Hermes·REA·프로젝트 설치/분리 경로가 재사용합니다. Homebrew npm 심볼릭 링크, Chrome/Edge 앱, Finder 폴더 열기, REA 기본 파일 선택창, 독립 소스의 .command 진입점을 연결했습니다. Windows 전용 설치는 Mac에서 명시적으로 거절하며 CUDA·키움 의존성 설치를 우회하지 않습니다. 모델·회사/대화·REA·금융 원본 기록은 이동하거나 삭제하지 않았습니다. 실제 확인 범위는 [공통 실행](backend/README.md), [REA 분석](modules/rea/backend/program_analysis/README.md), [Hermes](modules/hermes/backend/engine/README.md), [프로젝트 관리](modules/projects/backend/README.md)를 따릅니다. 금융 CUDA/키움·전체 학습·주문과 독립 ZIP의 타 컴퓨터 설치까지 완료했다는 의미는 아닙니다.
