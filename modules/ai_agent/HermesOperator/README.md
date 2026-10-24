# Hermes Operator

Hermes Original을 사람이 메뉴에서 직접 조작하는 대신 외부 Browser Use 에이전트가 화면으로 조작합니다.

- 별도 Python 3.12 가상환경과 Chromium을 `runtime/ai_agent/HermesOperator/`에 준비합니다.
- Chromium은 `headless=False`라 사용자가 AI의 클릭·입력을 실제 창에서 볼 수 있습니다.
- LLM 연결은 기존 Hermes Original 프로필의 `FREELLMAPI_API_KEY`와 FreeLLMAPI `base_url`을 자동 탐색하고 모델은 `auto`를 사용합니다.
- 브라우저 프로필은 전용 폴더에 보존합니다. 평소 쓰는 브라우저 프로필을 건드리지 않습니다.
- 사용자는 AI 에이전트 → Hermes 조종기 채팅에 자연어로 지시합니다. Operator는 Hermes UI를 직접 조작하고 결과 화면을 확인한 뒤 보고합니다.
- 소스/설정 파일을 우회 수정하지 않고 UI 조작을 우선합니다. 삭제·외부 공개·결제·인증정보 변경처럼 되돌리기 어려운 단계는 최종 실행 직전에 승인을 요구하도록 프롬프트에 제한합니다.

첫 사용은 **Browser Use 설치**를 한 번 누릅니다. 설치가 끝난 뒤 채팅 지시를 보내면 보이는 Chromium 창이 열립니다.
