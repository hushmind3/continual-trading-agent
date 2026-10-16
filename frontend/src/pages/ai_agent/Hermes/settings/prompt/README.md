# 시스템 프롬프트 설정

Hermes 설정의 시스템 프롬프트 입력·저장 화면입니다. `SystemPrompt.tsx`는 공통 Textarea·Button을 사용하며 단일 `/api`의 `ai_agent/Hermes/settings`를 읽고 `{system_prompt, read_only}`만 저장합니다. 모델·인증·MCP 설정을 함께 덮어쓰지 않습니다.

저장 위치는 `runtime/ai_agent/Hermes/platform-settings.json`입니다. 백엔드 `engine/worker.py`가 원본 AIAgent의 `ephemeral_system_prompt`에 사용자 지침을 추가합니다. 기본 도구 안내는 유지하고 다음 대화 요청부터 적용합니다. 빈 문자열을 저장하면 추가 지침을 제거합니다. 작업 중 변경은 서버와 화면 양쪽에서 거부합니다.

확인: 시스템 프롬프트 저장 UI 검사 통과. 별도의 원본 엔진 프로토콜 검사에서 저장 지침이 실제 모델 요청의 system 메시지에 포함되는 것을 확인했습니다. 이 검사는 가짜 모델 API를 사용하며 실제 GGUF 추론은 실행하지 않습니다.

읽기 전용 분석 체크박스는 read_only를 함께 저장합니다. 시스템 지침을 작성하는 것만으로 읽기 전용 권한이 켜지지는 않습니다. 켜면 코드 읽기·검색만 허용하며 명령·쓰기·MCP·컴퓨터 작업은 차단합니다. 서버가 권한값을 저장하지 못하면 저장 성공으로 표시하지 않습니다.
