# 개별 프롬프트 설정

용도: 기존 Hermes 설정 화면에서 조직 공통 및 총괄·직원별 지침을 편집합니다.

- 구현: `AgentPrompts.tsx`; 상위 `../Settings.tsx`, `../../agent_navigation.ts`의 개별 프롬프트 탭입니다. 공통 Select/Textarea/Button과 `../useAgentSettings.ts`를 사용합니다.
- API: 기존 단일 `/api`의 `ai_agent/Hermes/settings` GET/POST. 서버가 반환하는 `agent_prompt_profiles`를 표시하며 `agent_prompts`의 선택한 키만 저장합니다. 기본 지침 불러오기는 편집값만 바꾸며 저장해야 적용됩니다.
- 저장: 기존 `runtime/ai_agent/Hermes/platform-settings.json`. 새 DB나 모델 설정을 만들지 않습니다. 일반 대화의 시스템 프롬프트는 기존 탭에 남습니다.
- 적용: `backend/chat/prompt_profiles.py`의 기본값 위에 저장한 값을 반영합니다. `company.py`는 총괄 요청에 조직 공통+CEO를, `meetings.py`는 실제 Hermes 자식의 목표에 시스템 공통+조직 공통+해당 직군을 전달합니다. 실행 중 저장은 기존 유휴 검사로 거절하며 다음 요청부터 적용합니다. 일반 delegate_task의 임의 역할에는 이 편집값을 자동 매칭하지 않습니다.
- 확인: 실행 서버에서 설정 → 개별 프롬프트로 이동해 역할 선택·수정·저장·새로고침을 확인합니다. 일반 대화·모델·인증 설정은 변경하지 않습니다. 모델의 표현력이나 사실성 개선을 보장하지 않습니다.

실제 확인(2026-10-21): 기존 서버에 적용 후 8개 대상 표시, 총괄 지침 수정·저장·새로고침 유지·원래 지침 복구, CTO 전환, 390px 가로 넘침 없음, 브라우저 오류 0건을 확인했습니다. Python 구문·TypeScript·실제 프론트 빌드 통과. 이번 변경으로 모델 응답을 새로 생성하지 않았으므로 한국어 출력 개선 효과는 미확인입니다.
