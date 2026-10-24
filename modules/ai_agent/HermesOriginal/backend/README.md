# 헤르메스 원본 중메뉴

용도: AI 에이전트 → 헤르메스 원본 → 원본 화면의 실제 백엔드, 공식 원본·업데이트 경계와 한국어 패치를 관리합니다.

## 구현과 경로

- `original/manager.py`: 원본 화면 소메뉴의 `status/start/stop` API.
- `original/manager.py` → `manager.py` → 공통 `backend/ai_agent/manager.py` → `register.py`의 자동 등록 → 전체 메뉴 총괄 → 단일 `/api`.
- `launch.py`: 공식 PM 환경·한국어 패치를 사용해 원본 CLI를 실행합니다. CLI: 프로젝트 루트에서 `.venv/platform/bin/python modules/ai_agent/HermesOriginal/backend/launch.py <원본 인수>`.
- `runtime.py`: 원본 대시보드 시작·상태·명시적 중지만 담당합니다. 공식 업데이트가 PID를 교체하면 기존 호스트의 psutil로 소스·사용자 홈·포트·실제 대시보드 응답을 확인한 뒤 상태를 재연결합니다. 종료 시 소유 세션의 하위 프로세스도 함께 정리하고 마지막 포트를 유지합니다. Git 서브모듈의 `.git` 파일과 기존 `.git` 디렉터리를 모두 허용합니다.
- `../korean-ui.patch`: 현재 실행용 한국어 변경. 기준 버전·보관 폴더·복원 절차는 [한국어 패치 기준 안내](../README.md#한국어-패치)를 따릅니다.
- 등록·React 화면: [중메뉴 소유 폴더](../README.md).

공식 원본 설치·업데이트 위치는 `runtime/ai_agent/HermesOriginal/source/`로 유지합니다. 사용자 상태는 같은 담당 메뉴의 `home/`, 공식 PM 설치 도구는 `tools/`입니다. 이식 Hermes의 소스·환경·대화와 공유하거나 복제하지 않습니다. 원본 소스는 `.gitmodules`의 고정 버전 의존성이고, 설치된 패키지·홈·키·기록은 GitHub에 포함하지 않습니다.

## GitHub 복원과 처음 준비

프로젝트 루트에서 `git submodule update --init`으로 등록된 공식 소스를 받습니다. 플랫폼 설치 뒤 공식 PM 환경이 없는 새 설치에서만 다음을 실행합니다. 현재 설치본을 정리하는 과정에서 재설치하지 않습니다.

```sh
platform_root="$PWD"
cd runtime/ai_agent/HermesOriginal/source
HERMES_HOME="$platform_root/runtime/ai_agent/HermesOriginal/home" HERMES_RUNTIME_DIR="$platform_root/runtime/ai_agent/HermesOriginal/tools" "$platform_root/.venv/platform/bin/python" -m pm.cli install
```

한국어 패치 적용·웹 빌드는 [한국어 패치 기준 안내](../README.md#한국어-패치)를 따릅니다. 계정·모델·메신저 연결은 원본 설정에서 별도로 준비합니다.

## 업데이트와 확인

공식 업데이트는 기존 `source/`에서 원본의 기능으로 수행합니다. 새 공식 버전과 패치가 실제로 동작하는지 확인한 뒤 상위 플랫폼의 Git 의존성 커밋도 함께 갱신합니다. 실행 중인 기존 소스에 `git submodule update --remote`나 강제 checkout을 임의로 실행하지 않습니다. 한국어 패치의 버전 불일치·충돌 처리와 최신 적용 결과는 [기준 안내](../README.md#한국어-패치)에서 관리합니다.

macOS 게이트웨이는 모든 프로필을 처리하는 호스트 서비스 하나를 사용합니다. 이 설치본의 LaunchAgent는 `HERMES_HOME=runtime/ai_agent/HermesOriginal/home`, `HERMES_RUNTIME_DIR=runtime/ai_agent/HermesOriginal/tools`의 절대 경로를 사용하며 실행 인수는 `-p default gateway run --external-supervisor`입니다. 프로필 전용 게이트웨이를 시작해 오류 78이 난 경우 별도 프로필 서비스를 추가하지 않고 이 호스트 서비스의 경로와 상태를 확인합니다. 현재 경로를 맞춘 뒤 웹 화면에서 게이트웨이 실행 중을 확인했습니다. 설치·업데이트로 서비스 정의를 다시 생성하면 이 사용자 지정 도구 경로도 확인해야 합니다.

확인: 단일 API의 `ai_agent/HermesOriginal/status`, `#ai_agent/HermesOriginal`의 실제 원본 화면, 원본 `git rev-parse HEAD`, 패치의 `git apply --reverse --check`를 사용합니다. 현재 정리의 실제 실행 확인은 모듈 README의 최신 항목을 따릅니다. 원본 업데이트·모델 추론·외부 메신저 전체를 이번 정리에서 실행하지 않습니다.

## FreeLLMAPI 공용 연결

기존 프로젝트 설치본의 단일 `/api/projects/freellmapi/<설치 ID>/v1`을 OpenAI Chat 규격으로 사용합니다. 개별 업체를 이 메뉴에 직접 연결하지 않고 `auto`가 FreeLLMAPI의 활성 체인에서 고릅니다. 통합 키는 담당 `home/.env`에만 저장하고 Git에 올리지 않습니다.
공식 설치본 `cli/dist/index.js setup-hermes --profile shared --model auto`를 각 기존 `HERMES_HOME`에 실행해 `providers.freellmapi-shared`를 등록했습니다. 기본 홈과 다섯 기존 프로필에서 같은 연결을 선택할 수 있습니다. 현재 화면의 lead 프로필에도 등록했고 원본 모델 선택 UI에서 `freellmapi-shared · auto`를 주 모델로 적용했습니다. 다른 역할 프로필의 기존 주 모델은 유지합니다. 키·주소는 `FREELLMAPI_API_KEY`·`--url`로 전달하며 원본 설정 생성기가 병합합니다.
2026-10-25 실제 확인: 기본 프로필의 기존 CLI와 lead 프로필의 원본 웹 대화에서 `auto` 응답을 받았습니다. 장시간 작업·모든 도구의 전수 확인과는 구분합니다.

## 대화에서 공식 칸반 사용

작업판 화면과 채팅 도구 활성화는 별개입니다. 총괄 lead에는 공식 `launch.py -p lead tools enable kanban`을 적용해 `home/profiles/lead/config.yaml`의 `platform_toolsets.cli`에 칸반을 추가했습니다. 다른 역할의 실제 디스패처 작업자는 원본이 작업 수명주기 도구를 자동 제공합니다. 별도 협업 엔진·가짜 스킬·새 UI는 만들지 않습니다. [공식 도구 활성화 안내](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban#enabling-tools-for-a-chat-profile)를 따르며, 설정 전 대화는 도구 구성이 남으므로 공식 게이트웨이에 설정을 반영하고 기존 이력으로 재접속하거나 새 대화를 사용합니다.

사용 화면은 8766의 `#ai_agent/HermesOriginal` 안입니다. 현재 공용 보드의 식별자는 `service-lab`, 표시 이름은 AI 서비스 연구소입니다. 보드 이름 대신 식별자를 쓰거나 현재 보드를 기본으로 조회합니다. 2026-10-25 기존 원본 화면에서 목록·카드 상세 조회와 `t_ef5d284a` 댓글 등록·재조회·모델의 최종 확인 답변까지 검증했습니다. 카드 상태는 triage로 유지했고 신규 업무·작업자를 확인용으로 실행하지 않았습니다. 전송 오류 수정은 [프로젝트 실행 중계 안내](../../../projects/backend/README.md)를 따릅니다.
