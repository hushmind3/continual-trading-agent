# Sessions

List/create/read/archive sessions through the copied Hermes `SessionDB`. Tool call history is preserved for continuation. Session creation does not require a configured model. Archive hides a session without destroying history.

`session/rename`은 원본 SessionDB.set_session_title을 사용해 제목만 바꿉니다. ID와 메시지·도구 기록은 유지하고, 없는 대화·빈 제목·120자 초과는 거부합니다. 새 모델 호출은 하지 않습니다. test_hermes_port의 test_09는 원본 엔진 프로토콜로 이름 변경·기록 보존·프로세스 재시작 후 복원을 검사합니다(모델 API는 로컬 픽스처).
