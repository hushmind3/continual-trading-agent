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

확인: 단일 API의 `ai_agent/HermesOriginal/status`, `#ai_agent/HermesOriginal`의 실제 원본 화면, 원본 `git rev-parse HEAD`, 패치의 `git apply --reverse --check`를 사용합니다. 현재 정리의 실제 실행 확인은 모듈 README의 최신 항목을 따릅니다. 원본 업데이트·모델 추론·외부 메신저 전체를 이번 정리에서 실행하지 않습니다.
