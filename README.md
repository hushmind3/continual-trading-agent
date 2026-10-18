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

실행: **서버켜기.cmd**. 설치: **설치.cmd**. 세부 명령과 작업 보호는 [실행 안내](development/scripts/README.md)를 따릅니다.

운영 호스트는 `.venv/platform/`, 금융은 `modules/finance/.venv/`, 키움은 `modules/finance/.venv/kiwoom/`, REA는 `modules/rea/.venv/`, Hermes는 `modules/hermes/.venv/`를 사용합니다. 이전 루트 `.venv/`는 개발 검사·복구용이며 운영 업무 패키지의 공통 설치 위치가 아닙니다. 각 모듈의 의존성 명세·설정은 해당 모듈이 소유합니다.

npm 루트 workspace는 플랫폼 frontend만 관리합니다. REA의 Node 패키지는 `modules/rea/`, Hermes 브라우저 패키지는 `modules/hermes/backend/engine/browser/`에서 각 잠금 파일과 node_modules를 사용합니다.

데이터는 프로그램과 분리합니다. 가격 DB는 `data/market_prices.sqlite3`, REA 저장 프로젝트는 `runtime/rea/project_explorer/projects/`, Hermes 설정·대화는 `runtime/ai_agent/Hermes/`입니다. 서버·감시는 `runtime/platform/`, 공유 실행기는 `runtime/shared/engines/`에 둡니다. 모델 원본은 사용자가 지정한 바탕화면 모델 폴더에 유지합니다. 금융 설정은 `modules/finance/configs/`, REA 설정은 `modules/rea/configs/`에 있습니다. 비밀 설정·실제 패키지·실행 기록·휴지통은 Git 배포 대상이 아닙니다.

메뉴·API는 `modules/<id>/module.json`에서 자동 등록하며 중앙 코드에 기능별 import를 추가하지 않습니다. 지원 Node 백엔드는 동일 IPC 규격으로 연결할 수 있지만 OpenClaw 원본 설치·어댑터는 아직 수행하지 않았습니다.

현재는 금융·REA·Hermes의 소스·패키지 분리와 플랫폼 안에서의 폴더 탈착을 확인했습니다. 플랫폼 없이 실행할 완성 배포본·다른 PC 포터블 실행은 미완료입니다. 외부 앱의 지원 형식 ZIP 내보내기와 기본 모듈의 완전 독립 배포를 같은 완료 항목으로 취급하지 않습니다. 현재 검증과 남은 작업의 기준은 [모듈 안내](modules/README.md), 기능별 결과는 각 소메뉴 README입니다. 조사·검사 문서의 과거 결과는 해당 날짜와 조건에만 적용합니다.
