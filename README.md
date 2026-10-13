# Project platform

대메뉴는 **금융과 REA**입니다. 구조 이름은 영문, 기능 설명은 각 폴더 README에 있습니다.

| 위치 | 역할 |
| --- | --- |
| [backend/](backend/README.md) | 단일 API·전체 메뉴 총괄·금융 stockrl/·독립 rea/ |
| [frontend/](frontend/README.md) | React; 금융 pages/finance/·REA pages/rea/ |
| [development/](development/README.md) | scripts/·tests/·docs/ 개발 자료 통합 |
| [공식 금융 소스](backend/stockrl/finrl_trading/library/README.md) | 백엔드 내부의 FinRL-X 원본 |
| configs/ | 금융 설정·계약·인증 참조 |
| data/ | 실제 저장 데이터 |
| runtime/ | 실행 상태·작업·모델 도구 결과 |
| backend/rea/project_explorer/saved_projects/ | 저장된 REA 원본·추론 자료 (Git 제외) |

`.git/`·`.github/`는 Git/CI, `.venv/`·`.venv/kiwoom/`은 기존 설치 환경입니다. 데이터·설정·실행 상태 경로는 유지합니다. 키움 환경은 .venv/kiwoom/으로 통합 관리합니다. `휴지통/`은 폐기 전용이며 열람·실행·Git 등록 대상으로 사용하지 않습니다.

실행: **서버켜기.cmd**. 설치: **설치.cmd**.
금융/REA 하위 기능 → 소메뉴 매니저 → 대메뉴 → backend/menu_registry.py → backend/web_api.py의 단일 /api로 연결합니다.

변경 작업은 관련 작은 메뉴 README부터 읽습니다. 검사 명령은 [scripts 안내](development/scripts/README.md)에 있습니다.


npm 의존성: 루트 package.json·package-lock.json·node_modules/에서 통합 관리합니다. frontend/와 backend/rea/는 package.json을 갖는 npm workspaces입니다. 설치는 루트 npm ci, 프론트 실행·빌드는 npm run dev/build --workspace frontend입니다.
