# 헤르메스 모듈

용도: 기존 플랫폼 헤르메스를 주력으로 유지하고 공식 전체 기능·데이터·UI 연결을 관리합니다.

- 공식 전체 소스: `backend/engine/upstream/`. 선별 복사본 대신 공식 Git 서브모듈을 사용합니다. 기준 커밋과 가져오기 이력은 `backend/engine/provenance.json`입니다.
- 플랫폼 연결: `backend/engine/{launch,worker,official}.py`, `backend/native/`. 공식 AIAgent·ASGI 앱·게이트웨이·칸반 배정기를 사용하며 별도 대체 에이전트 루프를 만들지 않습니다.
- 화면: 기존 `frontend/chat/`와 조직 화면을 유지합니다. 모델·스킬·MCP와 전체 관리 기능은 공식 React 페이지를 플랫폼 공통 글꼴·색상·탭 안에 연결합니다. iframe으로 교체하지 않습니다.
- 주력 데이터: 기존 `runtime/ai_agent/Hermes/`. 일반·총괄 대화는 같은 state.db를 사용합니다. 공식 기능의 원래 프로필별 저장 구조와 기존 사업 기록은 유지하며 별도 자체 대화 DB를 추가하지 않습니다.
- 공용 도구: `runtime/shared/engines/hermes-pm/`. PM이 Python·Node·CUDA 실행기·브라우저·드라이버를 관리합니다. 메뉴별 Python 의존 환경은 같은 Hermes 홈의 공식 installs/에 보관합니다.
- 원본 메뉴는 업데이트·비교용 소스와 기존 데이터를 보존하며 주력 실행의 대화·모델 설정을 대신하지 않습니다.

처음 준비할 때만 프로젝트 루트에서 `git submodule update --init -- modules/hermes/backend/engine/upstream`, 이어 플랫폼 Python으로 `modules/hermes/backend/engine/setup.py`를 실행합니다. 기존 준비된 설치본을 확인 목적으로 재설치하지 않습니다.

연결·실행·실제 확인 범위는 [백엔드](backend/README.md), [엔진](backend/engine/README.md), [설정 화면](frontend/settings/README.md)을 따릅니다. 원본 모델 파일은 사용자 지정 폴더에 유지합니다. 폐기된 선별 소스·중복 설치기·UI는 휴지통에 보존하며 Git 배포에서 제외합니다.
