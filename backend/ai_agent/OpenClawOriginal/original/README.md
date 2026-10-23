# OpenClaw 원본 화면 소메뉴

용도: 공식 Control UI 실행·상태·중지를 단일 `/api`에 연결합니다.

- 구현: `manager.py`; `ai_agent/OpenClawOriginal/{status,start,stop}`.
- 직접 의존: `../runtime.py`; 중메뉴 `../manager.py`, 대메뉴 `../../manager.py`가 취합합니다.
- 프론트 ID: `ai_agent/OpenClawOriginal`; AI 에이전트 → OpenClaw 원본 → 원본 화면.
- 원본 설치본·설정·실행 상태는 담당 중메뉴 `runtime/ai_agent/OpenClawOriginal/`를 공유합니다. 별도 업무 API·설정 DB를 복제하지 않습니다.
- 실행·확인·업데이트·미확인 범위: [중메뉴 안내](../README.md).
