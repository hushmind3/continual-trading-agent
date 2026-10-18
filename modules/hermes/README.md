# Hermes 모듈

용도: 이식 Hermes의 소스·패키지·영속 데이터 소유와 플랫폼 연결 경계를 안내합니다.

- `module.json`: AI 에이전트 대메뉴 → Hermes 중메뉴와 API의 자동 등록 정보입니다.
- `backend/`: 이식된 원본 엔진과 기능별 Python 코드입니다. 상세 실행 안내는 `backend/README.md`를 봅니다.
- `frontend/`: 대화·모델·작업 환경·MCP·스킬·시스템 프롬프트 화면입니다. React/Vite/Tailwind와 플랫폼 공통 UI를 사용합니다.
- `runtime/ai_agent/Hermes/`: 프로그램 밖에 보존하는 설정·대화 DB·작업 기록입니다. 모듈 제거 대상이 아닙니다.
- `modules/hermes/.venv/`: Hermes 전용 Python·패키지 환경. `runtime/shared/engines/llama.cpp/`는 모델 실행기를 재사용합니다.

폴더 등록·제거는 공통 감시기가 감지해 빌드와 서버 적용을 처리합니다. 실행 중인 작업이 있으면 적용을 보류합니다. 원본 Hermes 외부 체크아웃은 필요하지 않습니다.

이 모듈은 플랫폼의 공통 UI·HTTP 통로와 공유 모델 실행기를 사용하며 Python/브라우저 패키지는 모듈 전용 환경에 설치합니다. 폴더 탈착과 독립 배포는 별개입니다. 플랫폼 없는 배포 패키지 생성과 외부 GitHub 프로젝트의 자동 변환은 아직 구현 완료로 취급하지 않습니다.

패키지 소유: Python은 모듈 내부 `.venv`, Node는 `backend/engine/browser/node_modules`, 명세와 잠금은 각 설치 폴더에 있습니다. 설정·대화 DB·MCP·스킬·작업 기록은 기존 runtime/ai_agent/Hermes에 보존하며 경로는 engine/locations.py에서 모듈 기준으로 계산합니다. Python/Node 버전 자체를 바꾸지 않았습니다.
