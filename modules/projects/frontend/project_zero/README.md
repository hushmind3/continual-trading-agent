# Project Zero 경영실

용도: 원본 앱의 대화·회의·사업 승인·작업 DB를 공통 React/Vite/Tailwind 화면으로 표시합니다. 원본 화면은 상단 버튼으로 유지합니다. 설치된 원본 파일을 수정하거나 별도 엔진·서버를 복제하지 않습니다.

- `Workspace.tsx`: 대화/회의/업무/사업안 소화면과 실제 실행 단계.
- `useWorkspace.ts`, `api.ts`: 단일 `/api`의 `projects/invoke`를 통해 원본 인증·API를 사용하고 `projects/harness`에서 실행 역할을 읽습니다. 숨겨진 탭에서는 조회를 멈추고 중복 조회를 막습니다.
- `ChatPane.tsx`, `MeetingsPane.tsx`, `JobsPane.tsx`, `BusinessPane.tsx`: 역할별 화면. 공통 UI와 MarkdownContent를 사용합니다.
- 원본 `/api/admin/platform/workspace`는 `../../backend/project_zero_state.py`가 기존 ASGI 앱에 등록하는 인증된 조회이며, 회의/대화/승인은 원래 API로 실행합니다. 하네스가 꺼지면 ProjectApp은 원본 UI를 표시합니다.

회의는 기본 CPO·CTO·CMO·CFO·QA의 별도 호출 후 CEO가 종합합니다. 진행 표시는 저장된 발언과 실제 하네스 역할에 근거하며 업무 큐 상태와 구분합니다. DealPage는 기본 제공 예제이며 새 사업의 기본 초안이 아닙니다. 승인 전 공개하지 않습니다.

확인: TypeScript/Vite, 격리된 원본 업무 검사, 실제 브라우저 검사. 실행하지 않은 모델 회의는 실제 모델 검증으로 기록하지 않습니다.

CEO 결론을 발언보다 먼저 표시하고, 회의 기록에는 시간을 표시합니다. 채팅의 작성 내용은 탭 전환에도 유지합니다. 회의·사업 검토는 기본적으로 현재 주제만 참고하며, 개발 지침·공유 기억을 추가하는 스위치는 회의가 없을 때 변경할 수 있습니다. 원본 대화/교훈은 삭제하지 않습니다.

현재 확인: TypeScript/Vite, 격리 업무/호환 41개·플랫폼 회귀 60개 통과. verify_project_zero_workspace.cjs는 실제 인증/기록과 모의 진행 상태를 구분해 PC1440/모바일390·탭 전환 입력 보존·가로 넘침/JS 오류 없음을 확인합니다. verify_project_zero_meeting.cjs --allow-local-model은 실제 다섯 전문가+CEO의 6개 세션·발언 저장·종합을 확인했으며, 시험 주제에서 선택되지 않은 DealPage 언급은 0건입니다. 회의가 매출/시장조사/제품 출시를 대신하지 않습니다. 결과는 runtime/projects/manage/verification 소속입니다. 새 회의 입력란은 기록이 있으면 접어서 현재 진행·CEO 결론을 먼저 표시합니다.
