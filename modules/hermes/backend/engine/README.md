# 공식 Hermes 실행 엔진

용도: 선별 복사 없이 공식 코어 전체와 플랫폼 어댑터의 경계를 관리합니다.

- `upstream/`: 공식 전체 Git 서브모듈. 현재 기준은 947e2c90caa18607ff49fc6761534e36d757138c이며 가져온 공식 트리는 21,193개 파일입니다. 실제 기능 수와 파일 수는 구분합니다.
- `prepare.py`: 버전 관리된 한글·호환 패치를 검사하고 적용합니다. 신규 체크아웃의 타입 검사 전에 실행하며 설치·Vite 빌드·worker 시작도 같은 패치를 사용합니다.
- `provenance.json`: 공식 출처·기준 커밋·이전 선별 소스 보관 위치입니다.
- `patches/platform.patch`: 한글 리소스와 플랫폼에 필요한 최소 호환 변경. 공식 기억·플러그인·게이트웨이·스킬·자동 배정 코드를 선별 삭제하지 않습니다.
- `launch.py`: 플랫폼 표준 Python은 시작만 담당하고 실제 worker는 PM이 관리하는 Python·의존성으로 실행합니다.
- 공식 도구 선택은 hermes_cli.tools_config._get_platform_tools(config, cli)로 해석합니다. 작업 환경 저장은 공식 platform_toolsets.cli에 반영하며 기존 자체 축소 목록은 실행 기준에서 제외했습니다.
- `worker.py`: 기존 대화·총괄·조직과 공식 AIAgent를 연결합니다. 공식 프로필의 모델·제공자가 실행 기준입니다. 기존 홈·SessionDB를 유지합니다.
- `official.py`: 공식 hermes_cli.web_server.app의 수명 주기·HTTP·관리 WebSocket을 같은 worker에서 실행합니다. `/api/ws`는 원본 gateway_runtime·gateway_client의 접속·티켓 절차로 실제 canonical owner에 전달합니다. 레거시 TUI sidecar에 잘못 연결하지 않으며 티켓은 worker 안에만 유지합니다. 예약·칸반 배정도 같은 공식 게이트웨이를 사용합니다.
- `bridge.py`: 기존 JSON-line IPC. `native/` → 중메뉴 manager → AI 에이전트 등록 → 전체 메뉴 → /api로 취합합니다.
- `setup.py`: 공식 pm install과 공식 npm 워크스페이스·TUI 빌드를 준비합니다. 구형 .venv·requirements 목록·별도 드라이버 설치기를 다시 만들지 않습니다.

공용 실행 도구는 `runtime/shared/engines/hermes-pm/`, 주력 상태·기억·모델 등록·PM 의존 환경은 `runtime/ai_agent/Hermes/`입니다. 모델 원본은 이동·재다운로드하지 않습니다. 원본 메뉴의 별도 홈을 주력 상태로 바꾸지 않습니다.

일반·총괄의 현재 native 실행과 외부 앱의 명시적 JSON 계획/읽기 전용 계약은 구분합니다. 조직 프롬프트·승인·회의 기록은 기존 확장 기능이며 공식 기억 관리자를 별도로 재구현하지 않습니다.

공식 CLI 전용 명령은 전체 기능의 명령 실행에서 공식 ChatPage·PTY·CLI를 직접 사용합니다. 기존 기본 프로필의 일반 대화 열기는 플랫폼 대화로 이어지고, 고급 명령 화면도 같은 공식 SessionDB를 사용합니다. 별도 명령 해석기를 복제하지 않습니다.

확인: 기존 서버의 official/info·official/catalog와 실제 대화·모델 관리 경로를 사용합니다. 가짜 모델·별도 검사 프로젝트를 만들지 않습니다. 공용 코드·빌드·외부 서비스의 실제 실행 여부는 각각 구분합니다. 상세 실제 결과는 상위 backend/README.md에 기록합니다.

## 공식 자동 검토 연결

`runtime_policy.configure_tools`는 공식 등록표의 memory·skills 도구 전체를 지연 대상에서 제외합니다. 원본 turn_finalizer의 자동 검토 조건뿐 아니라 검토 에이전트가 상속하는 skills_list·skill_view·skill_manage도 보존합니다. 읽지 않고 수정하는 것을 원본 검증에서 차단하며, 검증을 우회하지 않습니다. 검토·변경 장부·복원은 같은 Hermes 홈의 원본 구현을 사용합니다. 스킬 정리는 공식 게이트웨이의 curator 주기 작업을 따르며 별도 엔진·스케줄러·DB를 추가하지 않습니다.

2026-10-26 실제 확인: 기존 총괄 세션·기존 Ornith 9B의 공식 자동 검토가 유휴 대기 20초 뒤 시작하고, 기억을 갱신하며 verify-actual 스킬을 생성했습니다. YAML·설명 길이 오류 세 번은 원본 검증에서 거절됐습니다. 생성 장부 bdafebeb3602를 원본 rollback_entry로 생성 이전 상태로 되돌리고 다시 복원해 SHA-256 일치를 확인했습니다. 이후 드러난 조회 도구 미노출을 수정해 기존 9B 총괄의 skill_view 성공과 기억·스킬 도구 네 종류의 실제 노출을 확인했습니다. 수정 후 같은 9B의 실제 skill_view 호출과 자동 검토를 확인했습니다. Thinking 끄기·출력 한도 2,048의 일회성 조건에서 20초 유휴 대기 후 스킬 조회·기억 갱신·정상 종료까지 약 37초, 모델 3회로 완료됐습니다. 원본 로그는 result=memory이며 이번 후속 검토에서 스킬을 추가 수정하지는 않았습니다. 기존 Thinking 켜기·medium·출력 한도 없음에서는 10분 안에 첫 검토 응답을 끝내지 못해 해당 검증을 종료했습니다. 이 지연을 해결했다고 기록하지 않습니다.

기존 도구·실행 정책 검사 11개 통과, 윈도우 서버 적용 완료. 검증용 자동 검토 주기·Thinking·출력 한도는 모두 원래 설정(기억 10턴·스킬 기본 10회·Thinking 켜기·medium·출력 한도 0)으로 복구했고, 주 모델은 변경하지 않았습니다. 이 결과는 프로그램 자체의 성능 자동 비교·자동 채택이나 모델 가중치 학습의 성공을 뜻하지 않습니다. 외부 계정·채널·유료 서비스 전체 실행과 구분합니다.

## DSPy 선택 스킬

공식 optional-skills/mlops/research/dspy는 DSPy 사용 지침이며 Hermes의 자동 검토 자체가 DSPy·GEPA를 실행한다는 뜻은 아닙니다. 2026-10-26 기존 기본 프로필에서 공식 skills hub의 official/mlops/research/dspy를 설치해 enabled를 확인했습니다. 공식 PM이 선택한 의존 환경에 기존 패키지 버전을 고정한 채 DSPy 3.4.1·GEPA 0.1.4를 준비하고 hermes_bootstrap 활성화 이후 dspy.GEPA import·호출 가능 여부를 확인했습니다. 자동 검토·스킬 변경 장부와 같은 기존 공식 경로는 유지합니다. 실제 평가 자료로 최적화·성능 향상을 검증한 결과는 없으며 별도 자기개선 엔진·학습 DB·상시 최적화 루프를 만들지 않았습니다.

## 기존 대화의 공식 owner 연결

구형 플랫폼의 source=platform은 원본 local-session 마이그레이션 대상이 아니어서 동일 state.db여도 owner에서 기존 대화를 찾지 못했습니다. worker 초기화에서 메시징 경로·사용자 정보가 없는 이 구형 행만 공식 cli source로 바꿉니다. 변경 전에 기존 DB의 일관된 SQLite backup을 migrations/에 남기고 같은 DB의 state_meta에 변경 ID·복구 위치를 기록합니다. 대화·메시지·조직 연결 ID는 삭제하지 않습니다. 새 일반/총괄 대화도 원본 cli source를 사용합니다.

실제 확인(2026-10-26): 기존 37개 행의 ID 유지·source 변경, 전체 메시지 해시 동일, 기존 저장 ID 그대로 owner resume 성공. canonical runtime.describe·조회 RPC·subscription_id를 사용한 viewer detach 성공. 이 수정이 플랫폼의 모든 AIAgent 실행을 owner로 옮겼다는 의미는 아닙니다. 기존 회사·회의 확장의 원본 플러그인 연결과 실행 주체 일원화는 남아 있습니다.

공식 조직 SDK 연결은 ../chat/native_plugin.py를 사용합니다. core AIAgent·GatewayAgent·SessionDB를 복제하지 않으며, 원본 PluginContext에 조직 도구를 등록합니다. 기존 플랫폼의 직접 AIAgent 호출은 아직 남아 있습니다. 같은 기존 세션의 원본 GatewayAgent 도구 조회는 실제 성공했으나, 플랫폼 요청의 모델·추론·읽기 모드·목표/반복·승인·첨부·스트림 정책을 원본 client에 계승하는 전환은 완료되지 않았습니다. 모델 이름과 제공자가 서로 다른 기존 세션을 발견했으며 현재 선택과 맞추는 원본 GatewayAgent.switch_model의 실제 변경을 확인했습니다. 이를 플랫폼의 모든 전송 경로에 적용한 완료로 보고하지 않습니다.
