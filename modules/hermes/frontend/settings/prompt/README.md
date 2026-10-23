# 시스템 프롬프트 설정

용도: Hermes 전체의 대화·업무·기억 기본 지침과 사용자의 추가 지침을 편집합니다.

`SystemPrompt.tsx`는 공통 Textarea/Button과 단일 `/api`의 `ai_agent/Hermes/settings` GET/POST를 사용합니다. `system_prompt`만 저장하며 모델·인증 설정을 덮어쓰지 않습니다. 저장은 기존 `runtime/ai_agent/Hermes/platform-settings.json`을 사용합니다.

`backend/chat/prompt_profiles.py`의 SYSTEM_PROMPT는 사용자가 제공한 전체 기본 지침입니다. 기본 지침은 원본 Hermes 필수 도구 지침을 보존한 채 모든 요청에 적용합니다. 기존 사용자 지정 문자열은 삭제하지 않고 추가 지침으로 전달합니다. 설정 화면은 기본·사용자 설정 여부를 구분하고 기본 지침 불러오기 후 저장할 수 있습니다. 빈 문자열 저장은 사용자 추가 지침을 비우며 기본 지침은 유지합니다. 실행 중 저장은 기존 유휴 검사로 거절합니다.

직원별 지침·이름은 ../agent-prompts/README.md에서 설명합니다. 실제 모델 출력의 자연스러움은 선택 모델과 대화 맥락에도 영향을 받으므로 코드 구현·실제 관찰 결과를 구분합니다.
