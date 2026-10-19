# 선택형 회사 업무 연결

용도: 회사/사업안/직원 큐 규격을 제공하는 설치 앱을 실제 Hermes 제작 흐름에 연결하는 선택형 어댑터입니다. 저장소 이름으로 자동 적용하지 않습니다.

`company.py`는 명시적인 `workspace/connect(recipe=company-v1)`에서 앱 소유 integrations/hermes/workflow.py로 복사됩니다. 원본 앱의 database/venture_engine/operations 공개 함수를 사용하며 승인→요구사항→제작→검증을 순차 실행합니다. 생성물은 앱 소유 workspaces/<사업 ID>/에 저장합니다. 실패 시 후속 작업을 실패 처리하고 원본 기록은 보존합니다. 로컬 제작 승인은 외부 공개·결제·지출 승인이 아닙니다.

연결·실행기는 ../workspaces.py, ../app_worker.py, ../harness_hook.py, ../harness.py를 사용합니다. 원본 모델/API/Thinking 설정을 복제하지 않습니다. 연결을 끄거나 앱을 제거하면 어댑터도 적용되지 않습니다. 회귀는 development/tests/test_company_integration.py입니다.

2026-10-20 검증: 관련 회귀 72개 통과. 실제 원본 ASGI 자식 실행기의 승인 큐·모델 IPC·화면 조회·작업 중 재시작 보호와 실제 Node 테스트/빌드를 격리 환경에서 확인했습니다. 모델이 파일 없이 완료를 주장하거나 Node 검사가 실패하면 실패/후속 중단으로 기록합니다. 원본 sqlite context의 연결을 commit/rollback 뒤 명시적으로 닫아 검사·재시작 시 DB 핸들이 남지 않게 했습니다.

실제 승인 사업의 재개에서는 CPO의 5,589바이트 requirements.md 생성·완료와 CTO의 package.json·Vite·Vitest 설정 파일 작성을 확인했습니다. CTO 제작 중이며 QA는 대기입니다. 이 상태를 실제 제품 완성/QA 통과/서비스 공개/매출 발생으로 기록하지 않습니다. 실측 상태는 runtime/ai_agent/Hermes/verification/workspace-tabs/company-live.json에 분리합니다.

프론트 TypeScript 검사·Vite 빌드를 통과했습니다. 1440px·390px 브라우저 검사에서 원본 UI·4개 탭·각 대화 초안·공유 모델 설정·Markdown 제목/강조 렌더링을 확인했고, 스크립트 실행·가로 넘침·JavaScript 오류·검사용 모델 요청은 없었습니다. Markdown 합성 입력은 브라우저 DOM에만 삽입하고 제거하며 실제 대화 DB를 변경하지 않습니다.
