# Project platform

대메뉴는 **금융과 REA**입니다. 구조 이름은 영문, 기능 설명은 각 폴더 README에 있습니다.

| 위치 | 역할 |
| --- | --- |
| [backend/](backend/README.md) | 단일 API·전체 메뉴 총괄·금융 stockrl/·독립 rea/ |
| [frontend/](frontend/README.md) | React; 금융 pages/finance/·REA pages/rea/ |
| [development/](development/README.md) | scripts/·tests/·docs/ 개발 자료 통합 |
| [금융 학습·데이터](backend/stockrl/finrl/README.md) | 공식 FinRL/SB3와 자체 가격 저장·공급원 연결 |
| configs/ | 금융 설정·계약·인증 참조 |
| data/ | 실제 저장 데이터 |
| runtime/ | 실행 상태·작업·모델 도구 결과 |
| backend/rea/project_explorer/saved_projects/ | 저장된 REA 원본·추론 자료 (Git 제외) |

`.git/`·`.github/`는 Git/CI, `.venv/`·`.venv/kiwoom/`은 기존 설치 환경입니다. 데이터·설정·실행 상태 경로는 유지합니다. 키움 환경은 .venv/kiwoom/으로 통합 관리합니다. `휴지통/`은 폐기 전용이며 열람·실행·Git 등록 대상으로 사용하지 않습니다.

실행: **서버켜기.cmd**. 설치: **설치.cmd**.

프로젝트 앱 설치·분리·제거·독립 실행 ZIP/가져오기는 [프로젝트 관리 안내](modules/projects/README.md)를 따릅니다. 지원 앱의 Python 의존성은 앱 폴더에 보관하며 제거 때 함께 정리합니다. 설치/번역 때문에 사용자 모델을 자동으로 불러오지 않습니다. 미지원 구조의 모델 변환은 사용자가 켠 경우에만 실행합니다.
금융/REA 하위 기능 → 소메뉴 매니저 → 대메뉴 → backend/menu_registry.py → backend/web_api.py의 단일 /api로 연결합니다.

변경 작업은 관련 작은 메뉴 README부터 읽습니다. 검사 명령은 [scripts 안내](development/scripts/README.md)에 있습니다.


npm 의존성: 루트 package.json·package-lock.json·node_modules/에서 통합 관리합니다. frontend/와 backend/rea/는 package.json을 갖는 npm workspaces입니다. 설치는 루트 npm ci, 프론트 실행·빌드는 npm run dev/build --workspace frontend입니다.

현재 가격 DB는 data/market_prices.sqlite3입니다. FinRL-X와 Streamlit은 설치·실행 연결에서 제거했습니다. Expert 원본·패키지는 바탕화면 모델/experts/market(시장·시계열) 및 action(행동·정책)에 분류합니다. 최신 검증·정리 결과는 development/docs/finrl_x_removal.md를 읽습니다.

Expert 설정은 바탕화면 모델/experts/expert_registry.json(경로·선택 취합)과 각 원본 모델 폴더의 expert.json(모델 등록·설정·기록)에 있습니다. 프로젝트 configs/experts.json은 모델 폴더로 이동했습니다. 가중치와 원본 config 파일은 변경하지 않았습니다.
