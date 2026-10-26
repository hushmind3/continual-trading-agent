# Sessions

List/create/read/archive sessions through the copied Hermes `SessionDB`. Tool call history is preserved for continuation. Session creation does not require a configured model. Archive hides a session without destroying history.

`session/rename`은 원본 SessionDB.set_session_title을 사용해 제목만 바꿉니다. ID와 메시지·도구 기록은 유지하고, 없는 대화·빈 제목·120자 초과는 거부합니다. 새 모델 호출은 하지 않습니다. test_hermes_port의 test_09는 원본 엔진 프로토콜로 이름 변경·기록 보존·프로세스 재시작 후 복원을 검사합니다(모델 API는 로컬 픽스처).

총괄의 새 대화도 같은 session/create를 사용하며 company_id가 연결된 기존 조직인지 확인합니다. 새 UUID의 native SessionDB 세션에 조직 ID를 기록하고 기존 회사 도구 연결만 이어줍니다. 기존 총괄·직원·회의·사업 기록을 복제하거나 삭제하지 않습니다. session 및 sessions 응답은 company_id를 반환하고 session 응답의 metrics는 기존 model_config에 보존한 마지막 실행/누적 입력을 제공합니다. 세션 보관은 기록 삭제가 아닙니다.
