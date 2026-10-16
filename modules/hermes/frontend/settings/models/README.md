# 모델 선택과 연결

로컬 GGUF 선택·불러오기·내리기 또는 모델 서버 연결을 담당합니다. 작업 폴더·사용 도구·실행 한도는 별도 작업 환경 소메뉴입니다.

- ModelSettings.tsx: 로컬/서버 공통 탭, 실제 적재 상태와 명령 연결.
- LocalModelPicker.tsx: 이름 검색·모델 선택·파일 경로와 크기 표시. 검색해도 선택을 잃지 않습니다.
- ModelServerForm.tsx: 서버 주소·키·모델 입력. settings 저장 시 연결 필드만 전달합니다.
- ../useAgentSettings.ts: 설정 조회·실패 후 다시 불러오기.
- 공통 ui/SettingsSection·Primitives: 패널·읽기 실패·입력·키보드 탭.

단일 /api의 ai_agent/Hermes/settings, models/local, models, model/load, model/unload에 연결합니다. 화면 이동·검색·모델 선택만으로 로딩·다운로드·실행하지 않습니다. 실제 준비됨은 local_model.state를 따릅니다.

확인: frontend/tests/hermes-workspace.local-browser.spec.ts의 모델 검색·요청 경로·설정 실패 복구 검사. 모델 API는 픽스처로 대체하며 실제 추론을 시작하지 않습니다.
