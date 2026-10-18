# Hermes 모듈

용도: 이식 Hermes의 소스·패키지·영속 데이터 소유와 플랫폼 연결 경계를 안내합니다.

- `module.json`: AI 에이전트 대메뉴 → Hermes 중메뉴와 API의 자동 등록 정보입니다.
- `backend/`: 이식된 원본 엔진과 기능별 Python 코드입니다. 상세 실행 안내는 `backend/README.md`를 봅니다.
- `frontend/`: 대화·모델·작업 환경·MCP·스킬·시스템 프롬프트 화면입니다. React/Vite/Tailwind와 플랫폼 공통 UI를 사용합니다.
- `runtime/ai_agent/Hermes/`: 프로그램 밖에 보존하는 설정·대화 DB·작업 기록입니다. 모듈 제거 대상이 아닙니다.
- `modules/hermes/.venv/`: Hermes 전용 Python·패키지 환경. `runtime/shared/engines/llama.cpp/`는 모델 실행기를 재사용합니다.

폴더 등록·제거는 공통 감시기가 감지해 빌드와 서버 적용을 처리합니다. 실행 중인 작업이 있으면 적용을 보류합니다. 원본 Hermes 외부 체크아웃은 필요하지 않습니다.

이 모듈은 플랫폼의 공통 UI·HTTP 통로와 공유 모델 실행기를 사용하며 Python/브라우저 패키지는 모듈 전용 환경에 설치합니다. 폴더 탈착과 독립 배포는 별개입니다. 독립 실행 소스 ZIP은 프로젝트 관리에서 공통 API/UI 소스 복사본과 설치/실행 진입점을 함께 내보냅니다. 다른 PC의 신규 의존성 설치·원본 모델 추론 전체와 모든 외부 GitHub 프로젝트의 자동 변환까지 확인한 뜻은 아닙니다.

패키지 소유: Python은 모듈 내부 `.venv`, Node는 `backend/engine/browser/node_modules`, 명세와 잠금은 각 설치 폴더에 있습니다. 설정·대화 DB·MCP·스킬·작업 기록은 기존 runtime/ai_agent/Hermes에 보존하며 경로는 engine/locations.py에서 모듈 기준으로 계산합니다. Python/Node 버전 자체를 바꾸지 않았습니다.

독립 실행 소스: GitHub → 프로젝트 관리 → 설치된 프로젝트의 이 모듈에서 내보냅니다. 압축을 푼 뒤 `python run.py setup`, `check`, `run --port 8080`으로 설치·검사·실행합니다. 필요한 공통 API/UI는 ZIP 안의 복사본을 사용합니다. 기존 데이터·비밀 설정·모델은 자동 포함하지 않습니다. 형식·실제 확인 범위는 [프로젝트 관리](../projects/README.md)를 따릅니다.
