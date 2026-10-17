# 조립식 모듈

`modules/<id>/module.json`과 그 안의 backend/frontend를 하나의 프로그램 단위로 취급합니다. 중앙 등록 파일에 기능별 import나 메뉴를 추가하지 않습니다.

- `schema: 1`, 고유 `id`, `group: {id,title}`, 선택 `order`를 선언합니다.
- `backend: {namespace, entry, path?}`: 기본 path는 backend. entry가 MENU+router 또는 GROUP+ROUTERS를 제공합니다. 선택 hooks는 busy_reason/reserve_restart/cancel_restart/close입니다. register_host(app)은 프로젝트 정적 화면 제공처럼 공통 호스트 연결이 필요할 때만 사용하며 기능 API는 기존 단일 /api로 등록합니다.
- `frontend: {entry: "frontend/register.ts"}`: menus와 선택 registeredMenus(actions)를 export합니다. React/Vite/Tailwind 및 `@platform/ui` 공통 컴포넌트를 사용합니다.
- 외부 설치기의 `install_revision`이 있는 앱은 GitHub 대메뉴 아래 앱별 중메뉴로 취합합니다. 선택 `app_title`은 중메뉴 이름이며 이전 설치본은 기존 group 제목을 사용합니다. 프론트/백엔드 공통 등록 시 적용하므로 기존 소스·데이터·주소를 옮기거나 생성 파일을 수동 수정하지 않습니다. 플랫폼 포함 AI 에이전트/Hermes/MCP는 이 규칙의 대상이 아닙니다.
- `data`: 프로그램 밖의 영속 경로. `resources`: 기존 실행 환경·공통 실행기 경로. 모듈 탈착은 이 경로를 이동·삭제하지 않습니다.

공통 감시기가 등록 정보 변경을 감지해 실행 중 작업을 확인하고, import 사전 확인·타입 검사·빌드·서버 적용을 처리합니다. 작업 중에는 적용을 보류합니다. 설치 실패는 runtime/platform 로그에 남기며 사전 확인 실패 시 기존 서버를 종료하지 않습니다.

Hermes 코드는 hermes/backend와 hermes/frontend에 들어 있습니다. 원래 외부 Hermes 폴더는 사용하지 않습니다. Python 환경은 .venv/hermes, DB·기록·설정은 runtime/ai_agent/Hermes, 모델 실행기는 runtime/shared를 재사용합니다.

현재 finance와 rea의 등록 어댑터는 `legacy_shared_code: true`입니다. 이 두 기존 기능의 코드는 아직 backend/stockrl·backend/rea와 frontend/src/pages에 있으며, 완전한 프로그램 이동·독립성은 Hermes와 별도로 검증해야 합니다. 등록 어댑터를 전체 독립 이식 완료로 간주하지 않습니다.

## 최종 목표와 현재 경계

외부 저장소의 최초 구조 분석·변환도 플랫폼이 수행해야 합니다. 사용자가 직접 어댑터를 만드는 것을 최종 사용 흐름으로 삼지 않습니다. 기존 화면·공식 실행기를 우선 재사용하고, 변환한 프로그램의 실행을 확인한 뒤 등록합니다. 실패한 변환은 이유를 표시하며 성공으로 등록하지 않습니다.

등록된 프로젝트는 메뉴 이동과 기능 호출로 연결되고, Hermes는 허용된 작업 범위 안에서 다른 프로젝트의 소스를 수정·검증할 수 있어야 합니다. 분리 배포에는 필요한 공통 코드·의존성을 포함하고 플랫폼이 없는 환경에서 실행 확인이 필요합니다. 모듈 폴더 분리만으로 독립 배포를 검증했다고 보고하지 않습니다. Expert 선택·조합·분리도 같은 소유권·의존성 확인 원칙을 따릅니다.

현재 구현은 등록 규격, 자동 메뉴/API 연결, 작업 보호, 자동 빌드·적용과 Hermes 프로그램 폴더 탈착입니다. [프로젝트 설치·관리](projects/README.md)는 공개 GitHub 검색·주소 등록, 지원 실행 구조의 자동 어댑터, 기존 Hermes를 통한 추가 변환 요청, 원본 UI 실행 확인·설정·업데이트·분리를 제공합니다. 임의의 모든 저장소가 자동 변환된다고 보장하지 않습니다. 프로젝트 간 공통 협업 도구, 독립 배포 패키지 생성기와 Expert 공통 규격은 후속 구현 대상입니다.
