# OpenClaw 원본 중메뉴

용도: AI 에이전트 → OpenClaw 원본 → 원본 화면의 실제 백엔드와 공식 Gateway 설치·업데이트 경계를 관리합니다.

## 구현과 경로

- `original/manager.py`: `ai_agent/OpenClawOriginal/{status,start,stop}` 소메뉴 API.
- `original/manager.py` → `manager.py` → 공통 `backend/ai_agent/manager.py` → `register.py`의 자동 등록 → 전체 메뉴 총괄 → 단일 `/api`.
- `launch.py`: 원본 Node CLI를 실행하고 담당 메뉴의 `home/`만 사용합니다.
- `runtime.py`: 원본 Gateway의 PID·명령·상태를 관리합니다. Gateway는 기존 19021 루프백 주소를 사용합니다.
- `frame_policy.mjs`: 원본 파일을 패치하지 않고 내장 화면의 프레임·원격 접근 정책만 연결합니다.
- React 화면·원격 접근·기존 확인 결과: [중메뉴 소유 폴더](../README.md).

공식 원본 설치·업데이트 위치는 `runtime/ai_agent/OpenClawOriginal/source/`로 유지합니다. 설정·대화는 `home/`, 전용 Node는 `tools/node/bin/node`, 실행 상태·로그는 담당 메뉴 runtime에 둡니다. 원본 소스만 `.gitmodules`의 고정 버전으로 등록하고 패키지·홈·키·실행 기록은 제외합니다.

## GitHub 복원과 처음 준비

프로젝트 루트에서 `git submodule update --init`으로 원본 99599dbf83d67b5feb27df2ffcc22ae0f18f00d1을 복원합니다. 새 Mac 설치에는 원본 package.json의 Node 조건 `>=24.22.1 <25 || >=26.12.1`과 `pnpm 12.15.0`이 필요합니다. 현재 설치본의 도구는 다시 설치하지 않습니다.

호환되는 Node를 이미 설치한 새 환경에서는 `runtime/ai_agent/OpenClawOriginal/tools/node/bin/node`에 그 실행 파일을 준비합니다. 기존 경로가 있으면 덮어쓰지 않습니다. 공식 source 폴더에서 `pnpm install --frozen-lockfile`, `pnpm build`, `pnpm ui:build`로 원본 의존성·빌드를 준비합니다. 사용자 계정·모델 연결은 원본 대시보드에서 별도로 설정합니다. 원본 앱의 다른 PC 신규 설치는 이번 정리의 확인 범위에 포함하지 않습니다.

## 업데이트와 확인

공식 업데이트는 기존 `source/` 작업 트리에서 수행합니다. 원본 Git 원격과 설치 경로를 바꾸지 않으며, 상위 플랫폼은 검증한 버전을 Git 의존성 커밋으로 기록합니다. 새 버전의 실제 실행을 확인한 뒤 그 커밋을 상위 `main`에 함께 반영합니다. 실행 중인 원본에 강제 checkout이나 `git submodule update --remote`를 임의로 실행하지 않습니다.

확인: `ai_agent/OpenClawOriginal/status`와 `#ai_agent/OpenClawOriginal`에서 실제 Gateway·Control UI를 확인합니다. 공식 `gateway call status --json`은 실행 중 업무 확인에 사용하며 모델 호출을 대신하지 않습니다. 이번에는 업데이트·재다운로드·재설치·모델 추론을 확인 목적으로 실행하지 않습니다.

## FreeLLMAPI 공용 연결

기존 프로젝트 설치본의 단일 `/api/projects/freellmapi/<설치 ID>/v1`을 OpenAI Chat 규격으로 사용합니다. 개별 업체를 이 메뉴에 직접 연결하지 않고 `auto`가 FreeLLMAPI의 활성 체인에서 고릅니다. 통합 키는 담당 `home/.env`에만 저장하고 Git에 올리지 않습니다.
공식 설정의 `models.providers.freellmapi`와 `agents.defaults.model`을 사용합니다. 이 설치의 기본 에이전트 ID는 `dev`입니다. 실제 확인 명령은 `launch.py agent --agent dev --message <메시지> --json`이며, `--deliver` 없이 기존 Gateway를 사용합니다.
2026-10-25 실제 확인: 기존 설치에서 `auto` 대화가 `OK`를 반환했습니다. 장시간 작업·모든 도구의 전수 확인과는 구분합니다.
