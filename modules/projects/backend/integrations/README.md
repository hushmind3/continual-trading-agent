# 회사/조직 기록 어댑터

용도: Project Zero 원본 UI/DB를 기존 Hermes 총괄이 사용하는 업무 기록 도구로 연결합니다.

`company_records.py`는 명시적인 company-v1 연결에서 앱 소유 integrations/hermes/workflow.py에 설치됩니다. 원본 DB의 사업안·승인·업무·회의록과 인증을 재사용하고, 별도 planner/provider/직원 실행 루프는 사용하지 않습니다. 소유자가 직접 지시한 일반 업무는 사업안 없이 기록할 수 있고, 모델이 제안한 신규 사업은 소유자 승인 뒤 실행합니다. 역할·순서는 총괄이 선택합니다.

연결: workspaces.py → app_worker.py → 인증된 /api/admin/hermes/records. 대화/도구 실행은 modules/hermes/backend/chat/company.py의 native SessionDB/registry와 일반 chat/Goal/Loop입니다. 생성물은 앱 소유 workspaces/<사업 ID 또는 owner-tasks>/에 남습니다. 외부 공개·계정 인증·유료 지출은 실제 승인/연결이 필요합니다.

검사: development.tests.test_company_integration, test_company_conversation. 실제 원본 ASGI/DB로 인증·소유자 승인·고정 큐 없음·임의 역할 순서·중복 시작 방지·직접 지시·실패·회의 기록·adapter 갱신/롤백을 확인했습니다. 이전 회사 provider/pipeline와 company_context 보정 잔재는 의존성을 제거하고 프로젝트 휴지통으로 이동했습니다.

실제 견적서 사업의 이전 CPO 성공/CTO TimeoutError/QA 선행 실패는 보존합니다. 새 native 실행의 실제 결과와 UI 검증은 Hermes chat/README.md 및 해당 verification 자료를 따릅니다. DB 활용 학습·파인튜닝·강화학습은 현재 구현/검증 완료 항목이 아닙니다.

2026-10-20 실행 연결 보정: 새 긴 목표 누락·이전 터미널 CWD 잔류·자식 npm의 IPC 입력 상속·불투명한 HTTP 오류를 수정했습니다. 실제 native 실행에서 설치 → 오류 수신 → 소스 수정 → 최초 Vite 빌드(exit 0, 2.21초)를 확인했습니다. 관련 회귀 64개와 실제 총괄 수치/사업 패널을 확인했습니다. 제품 누락 기능은 Codex가 직접 보완했으며 로컬 견적 도구의 12개 검사·타입/빌드·브라우저 8개 시나리오가 통과했습니다. 무개입 제품 개발/공개/매출 검증과 구분합니다. 자료와 범위는 연결된 제품 README/verification 및 Hermes 대화 README를 따릅니다.

recall/remember 기존 기록 재사용: 새 DB·새 테이블·별도 임베딩 서버 없이 기존 ventures/jobs/ceo_meetings/ceo_experiences/ceo_lessons를 조회합니다. remember는 원래 record_lesson을 사용하며 origin에 종류·사업 ID·주제 키를 저장합니다. 같은 키의 새 결정이 이전 결정을 대체해 회상되지만 원문은 삭제하지 않습니다. 조회는 관련 사업과 조직 공통 결정/제약으로 제한하며 4,200자 이하로 반환합니다. finish는 원래 경험 기록 함수를 사용해 실제 성공/실패를 남깁니다. 기존 레코드 인증과 단일 /api는 그대로입니다.

확인: 원본 회사 ASGI/DB 및 native 연결 관련 26개 검사로 오래된 결정 조회·정정 우선·사업 범위 분리·미완료/실패 계승·새 테이블 없음·원문 보존·직접 Git 승인·활성 문맥 중복 제외를 확인합니다. 실제 서버의 기존 견적서 사업 회상도 추가 모델 호출 없이 확인했습니다. 실제 9B 응답의 길이/회의 빈도와 모든 자연어의 회상 정확도를 보장하는 검사는 아닙니다.

회의 탭 연결(2026-10-21): ../conversation.py의 읽기 전용 meetings 액션이 기존 앱의 인증된 /api/admin/meetings, /api/admin/hermes/records(overview), /api/admin/team을 단일 플랫폼 API로 조회합니다. 기존 ceo_meetings와 jobs를 그대로 사용하며 원본 회의 실행 API를 호출하지 않습니다. 직군 정의는 원본 앱에서 취합하고 프론트에 직원 목록을 복제하지 않습니다.

회의 조회 실제 확인: 기존 설치본의 meetings 응답으로 회의 1개와 원본 role/statement, TEAM_ROLES 7개, 기존 jobs 12개를 반환했습니다. 설치본 원본·DB를 재생성하거나 회의 실행 API를 호출하지 않았습니다.

실시간 회의: 기존 ceo_meetings/ventures를 재사용하는 meeting_start/read/resume/turn/proposal/finish 요청을 제공합니다. 설치본은 원래 workspaces.adapter의 해시 검사와 원자 교체로 갱신하므로 재설치하지 않습니다. 부분 발언은 ID로 갱신하고 출처·자식 세션 ID를 보존합니다. 재검토는 기존 pending 초안을 revising으로 잠그고 같은 ID를 pending으로 갱신합니다. 원래 소유자 승인 API도 pending만 허용합니다. 새 테이블·회사 planner·재다운로드는 없습니다.
