# 공식 Hermes 실행 엔진

용도: 선별 복사 없이 공식 코어 전체와 플랫폼 어댑터의 경계를 관리합니다.

- `upstream/`: 공식 전체 Git 서브모듈. 현재 기준은 947e2c90caa18607ff49fc6761534e36d757138c이며 가져온 공식 트리는 21,193개 파일입니다. 실제 기능 수와 파일 수는 구분합니다.
- `prepare.py`: 버전 관리된 한글·호환 패치를 검사하고 적용합니다. 신규 체크아웃의 타입 검사 전에 실행하며 설치·Vite 빌드·worker 시작도 같은 패치를 사용합니다.
- `provenance.json`: 공식 출처·기준 커밋·이전 선별 소스 보관 위치입니다.
- `patches/platform.patch`: 한글 리소스와 플랫폼에 필요한 최소 호환 변경. 공식 기억·플러그인·게이트웨이·스킬·자동 배정 코드를 선별 삭제하지 않습니다.
- `launch.py`: 플랫폼 표준 Python은 시작만 담당하고 실제 worker는 PM이 관리하는 Python·의존성으로 실행합니다.
- 공식 도구 선택은 hermes_cli.tools_config._get_platform_tools(config, cli)로 해석합니다. 작업 환경 저장은 공식 platform_toolsets.cli에 반영하며 기존 자체 축소 목록은 실행 기준에서 제외했습니다.
- `worker.py`: 기존 대화·총괄·조직과 공식 AIAgent를 연결합니다. 공식 프로필의 모델·제공자가 실행 기준입니다. 기존 홈·SessionDB를 유지합니다.
- `official.py`: 공식 hermes_cli.web_server.app의 수명 주기·모든 HTTP 기능·WebSocket을 같은 worker에서 실행합니다. 실제 게이트웨이를 준비해 예약·칸반 배정도 공식 경로를 사용합니다.
- `bridge.py`: 기존 JSON-line IPC. `native/` → 중메뉴 manager → AI 에이전트 등록 → 전체 메뉴 → /api로 취합합니다.
- `setup.py`: 공식 pm install과 공식 npm 워크스페이스·TUI 빌드를 준비합니다. 구형 .venv·requirements 목록·별도 드라이버 설치기를 다시 만들지 않습니다.

공용 실행 도구는 `runtime/shared/engines/hermes-pm/`, 주력 상태·기억·모델 등록·PM 의존 환경은 `runtime/ai_agent/Hermes/`입니다. 모델 원본은 이동·재다운로드하지 않습니다. 원본 메뉴의 별도 홈을 주력 상태로 바꾸지 않습니다.

일반·총괄의 현재 native 실행과 외부 앱의 명시적 JSON 계획/읽기 전용 계약은 구분합니다. 조직 프롬프트·승인·회의 기록은 기존 확장 기능이며 공식 기억 관리자를 별도로 재구현하지 않습니다.

공식 CLI 전용 명령은 전체 기능의 명령 실행에서 공식 ChatPage·PTY·CLI를 직접 사용합니다. 기존 기본 프로필의 일반 대화 열기는 플랫폼 대화로 이어지고, 고급 명령 화면도 같은 공식 SessionDB를 사용합니다. 별도 명령 해석기를 복제하지 않습니다.

확인: 기존 서버의 official/info·official/catalog와 실제 대화·모델 관리 경로를 사용합니다. 가짜 모델·별도 검사 프로젝트를 만들지 않습니다. 공용 코드·빌드·외부 서비스의 실제 실행 여부는 각각 구분합니다. 상세 실제 결과는 상위 backend/README.md에 기록합니다.

## 공식 자동 검토 연결

`runtime_policy.configure_tools`는 지연 도구 모드에서도 공식 `memory`·`skill_manage`를 숨기지 않습니다. 원본 turn_finalizer는 이 도구들의 실제 노출 여부로 자동 기억·스킬 검토를 결정하므로, 총괄의 간소화된 도구 목록 때문에 검토를 건너뛰지 않게 합니다. 검토·주기·저장·변경 장부·복원은 원본 구현과 같은 Hermes 홈을 사용합니다. 스킬 정리는 이미 실행 중인 공식 게이트웨이의 curator 주기 작업을 따르며 별도 스케줄러를 추가하지 않습니다.

확인: 기존 도구·실행 정책 검사 11개 통과. 새 자기 코드 평가·자동 채택 엔진이나 별도 DB를 추가한 것이 아니며, 검사 통과를 실제 자동 개선·성능 향상의 성공으로 기록하지 않습니다.

실제 확인(2026-10-26): 기존 총괄 세션·기존 Ornith 9B로 공식 memory 도구의 저장 성공과 같은 Hermes 홈의 memories/USER.md 영속화를 확인했습니다(64.4초). 실제 도구 목록에 memory·skill_manage가 함께 표시됩니다. 이 요청은 명시적인 기억 저장이며 자동 background_review·스킬 개선·성능 비교·자동 채택까지 실행한 증거는 아닙니다. 별도 자기개선 프로그램·스케줄러·DB·검사 파일을 추가하지 않았습니다.
