# Project Zero 경영실

용도: 설치된 원본 앱의 대화·회의·승인·업무 기록을 공통 React/Vite/Tailwind UI로 표시합니다. 원본 UI는 상단에서 별도로 엽니다.

## 구현과 연결
- `Workspace.tsx`, `useWorkspace.ts`, `api.ts`: 대화/회의/업무/사업안 화면, 원본 인증과 비동기 상태 조회. 단일 `/api`의 `projects/invoke`, `projects/harness`를 사용합니다.
- `ChatPane.tsx`: 대화 입력 보존·CEO 보고. `ExecutionPlanCard.tsx`는 기본 4줄 요약과 승인하고 실행/보류 버튼이며 담당·산출물·완료 기준은 상세로 접습니다.
- `MeetingsPane.tsx`: 실제 역할별 발언 저장 수와 현재 발언자. CEO 결론을 먼저 표시하고 개별 발언은 접습니다.
- `JobsPane.tsx`: 실제 실행 큐·오류·산출물과 역할별 페르소나/책임. `BusinessPane.tsx`는 원래 사업안 승인과 실제 공개 제품을 구분합니다.
- 원본 앱의 `/api/admin/platform/workspace`, `/meeting-plans/{id}/prepare`, `/meeting-plans/{id}/decision`, `/discussion-context`는 [백엔드 안내](../../backend/README.md)의 실행 시 호환 어댑터가 등록합니다. 원본 소스·UI·DB를 복제하지 않습니다.

## 현재 동작
일반 CEO 대화는 문맥을 이어 직접 답하며 JSON 전송 계약만으로 계획 단계라고 표시하지 않습니다. 대화 intent는 실행 업무를 만들지 않습니다. CPO는 요구사항·사용자 흐름·화면 구성, CTO는 기술 설계·구현, QA는 실제 검증을 맡습니다. 실제 요청에 대한 직원 실행·회의·승인 상태는 별개로 표시합니다.

사용자가 선택하지 않은 원본 예제 상품의 과거 AI 답변/교훈/회의를 새 사업의 근거로 재사용하지 않습니다. 원본 기록은 화면과 DB에 보존합니다. 예제 자체를 질문하거나 실제 승인된 제품인 경우는 구분합니다.

회의는 공유 모델의 전문가 5회와 CEO 종합 1회입니다. CEO 실행안은 승인 전 업무를 만들지 않습니다. 승인 시 원본 agent_task 큐에 순서대로 등록하고 선행 산출물을 전달하며 실패 시 후속 실행을 중단합니다. 기존 회의는 실행안 작성 버튼으로 CEO 종합만 다시 요청할 수 있고, 저장된 실제 초안이 유효하면 모델 재호출 없이 복구합니다. 지출·외부 공개·메일은 별도 승인 대상입니다.

회의·대화는 기본 현재 앱 주제만 참고합니다. 개발 지침·공유 기억을 포함하는 옵션은 회의 준비에서 선택합니다. 일반 직원의 코드 실행은 원래 도구와 권한을 유지합니다. 앱 내부 주문/장부를 사용자의 다른 사업 실적으로 확대 해석하지 않습니다.

## 확인과 한계
`development/scripts/verify_project_zero.py`: 원본 소스 사본·임시 DB·모의 모델로 업무/호환 회귀. `development/tests/test_project_harness.py`: 하네스 계약·문맥·상태 분류. `verify_project_zero_workspace.cjs`: 실제 로컬 인증/역할과 별도 모의 진행·승인 상태, PC1440/모바일390·입력 보존·가로 넘침/JS 오류 검사. 사용자 모델은 호출하지 않습니다.

`verify_project_zero_context.py`: 원본 AIAgent→가짜 API 전송에서 호스트/경로 제외 확인. 실제 회의 6회 호출과 실제 CEO 실행안 1회 생성·승인 대기·업무 0개는 이전 실측이며 `runtime/projects/manage/verification/`에 있습니다. 전체 발언 품질·홈페이지 제작·외부 배포는 검증하지 않았습니다. 이번 보정의 통제된 실제 대화 검사는 아래에 구분합니다.

일반 역할 질문은 role_reference로 분류해 등록된 7개 역할 정보만 전달합니다. 특정 프로젝트의 최근 작업/진행 상태를 묻는 질문은 이 경로로 축소하지 않습니다. 과거 회의는 회의·발언·실행안 관련 질문에만 연결합니다. 실제 첫 역할 답변에서 DealPage는 나오지 않았지만 과거 금융 주제를 재사용한 것을 발견해 추가한 문맥 경계입니다. 원본 대화·회의는 삭제하지 않습니다.

최종 확인(2026-10-19): 격리 원본/업무 51개·하네스 19개, TypeScript·Vite, PC1440/모바일390 UI 통과. `verify_project_zero_dialogue.cjs --allow-local-model`로 원본 CEO에 실제 질문 2회를 보냈습니다. 역할 질문은 12초에 CPO/CTO/QA 책임을 답했고, 여행 홈페이지 아이디어 대화는 58초에 두 가지 대안을 답했습니다. 두 경우 모두 새 회의/실행 업무 0개, 요청하지 않은 예제·금융매매 프로젝트 언급 0건이었습니다. 역할 질문에서 과거 매출 0원 등의 사업 상태 주장도 없었습니다. 초기 실패와 재검증은 `project-zero-dialogue-live-before.json`, `project-zero-dialogue-live.json`으로 분리 보존합니다. 결과·화면은 runtime/projects/manage/verification 소속입니다. 이 2개 질문의 통과를 모든 주제/향후 답변에 대한 보장으로 기록하지 않습니다.
