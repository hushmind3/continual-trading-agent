# 직원별 프롬프트 설정

용도: 고유 식별자를 가진 직원의 이름·전문성·실행 책임과 조직 공통 지침을 편집합니다.

- 구현: AgentPrompts.tsx와 ../Settings.tsx, ../../agent_navigation.ts. 공통 Textarea/Button, 전체 편집칸, 변경분 일괄 저장을 사용합니다.
- API: 기존 단일 /api의 ai_agent/Hermes/settings GET/POST. agent_prompts 키는 common 또는 등록된 직원 UUID입니다. agent_prompt_profiles에는 표시 이름·기본값·사용자 설정 여부가 있습니다.
- 저장: 기존 runtime/ai_agent/Hermes/platform-settings.json의 staff_registry·manager_staff_id·agent_prompts. 별도 직원 DB나 에이전트 엔진을 만들지 않습니다.
- 이름은 지침의 이름 행에서 읽으며 ID는 이름과 무관하게 유지됩니다. 전문성·판단·실행 책임은 실제 프롬프트가 결정합니다. 기본 프롬프트는 사용자의 최종 실행 지시 원문이며 기존 사용자 설정은 보존합니다.
- 실제 위임: 원본 AIAgent._dispatch_delegate_task에서 tasks[].staff_id를 검증하고 해당 직원의 시스템·조직·개별 지침을 context에 넣습니다. 원본 자식·도구·작업 공간·중단·승인·결과 전달 기능을 재사용합니다. 회의는 별도의 실제 검토 기능이며 실행 위임을 대체하지 않습니다.
- 회의 직원은 기존 company_recall로 관련 업무·결정·경험을 조회합니다. 과거 총괄 명령이 담긴 대화 전문은 직원 조회 결과에 자동 주입하지 않습니다. 일반 session_search·기억·스킬은 총괄과 실행 에이전트에서 원본 기능을 유지합니다.
- 사업 승인은 기존 단일 API로 처리하고 승인된 작업 공간에서 원본 LoopManager의 자율 제작·운영을 시작합니다. 완료 산출물·실패·재검증·다음 작업과 운영을 이어가며 외부 공개·계정 인증·결제·지출은 필요한 승인을 유지합니다. 중지·재개는 기존 대화 기능을 사용합니다.
- 이관: ../../../backend/chat/staff_migration.py. 폐기된 역할 코드의 일회성 데이터 변환만 담당하며 실행 시 호환 ID로 쓰지 않습니다. 기존 설정·회사/원본 SessionDB·설치 소스/UI를 백업하고 기록 건수·DB 무결성을 검사합니다. 실패 시 복원하며 이후 같은 직원 ID를 재발급하지 않습니다.

실제 확인 범위는 최종 검증 결과에 기재합니다. 코드 연결·모델 실행·실제 출시·매출은 서로 다른 단계이며 검증하지 않은 성과를 완료로 보고하지 않습니다.

조직 위임의 결과 전달: 플랫폼 worker에는 원본 CLI/gateway의 백그라운드 결과 재주입 소비자가 없으므로, 회사 직원 위임은 원본 delegate_task의 동기 batch를 호출합니다. 원본 자식 병렬 실행·도구·중단·깊이/일시정지 guard는 유지하며 총괄은 실제 반환 결과를 받은 뒤 보고합니다. 일반 대화의 원본 background 위임은 변경하지 않습니다.
