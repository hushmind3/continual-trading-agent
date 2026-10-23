# 헤르메스 원본 화면 소메뉴

용도: 원본 대시보드 실행·상태·중지 API를 기존 단일 `/api`에 제공합니다.

- 구현: `manager.py`; `ai_agent/HermesOriginal/{status,start,stop}`.
- 직접 의존: `../runtime.py`; 중메뉴 `../manager.py`, 대메뉴 `../../manager.py`가 취합합니다.
- 프론트 ID: `ai_agent/HermesOriginal`. 메뉴 표시는 AI 에이전트 → 헤르메스 원본 → 원본 화면입니다.
- 설정·기록·공식 설치본은 중메뉴의 `runtime/ai_agent/HermesOriginal/`에서 함께 관리합니다. 소메뉴가 별도 서버·DB·엔진을 복제하지 않습니다.
- 실행·확인·업데이트·미확인 범위: [중메뉴 안내](../README.md).
