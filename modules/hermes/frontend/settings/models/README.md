# 모델 선택과 연결

로컬 GGUF 선택·불러오기·내리기 또는 모델 서버 연결을 담당합니다. 작업 폴더·사용 도구·실행 한도는 별도 작업 환경 소메뉴입니다.

- ModelSettings.tsx: 로컬/서버 공통 탭, 실제 적재 상태와 명령 연결.
- LocalModelPicker.tsx: 이름 검색·모델 선택·파일 경로와 크기 표시. 검색해도 선택을 잃지 않습니다.
- ModelServerForm.tsx: 서버 주소·키·모델 입력. settings 저장 시 연결 필드만 전달합니다.
- ../useAgentSettings.ts: 설정 조회·실패 후 다시 불러오기.
- 공통 ui/SettingsSection·Primitives: 패널·읽기 실패·입력·키보드 탭.

단일 /api의 ai_agent/Hermes/settings, models/local, models, model/load, model/unload에 연결합니다. 화면 이동·검색·모델 선택만으로 로딩·다운로드·실행하지 않습니다. 실제 준비됨은 local_model.state를 따릅니다.

확인: frontend/tests/hermes-workspace.local-browser.spec.ts의 모델 검색·요청 경로·설정 실패 복구 검사. 모델 API는 픽스처로 대체하며 실제 추론을 시작하지 않습니다.

ModelRuntimeControls.tsx는 공통 Input/Select/Button으로 현재 모델의 문맥 한도·Thinking과 도구 설명 전달 방식을 표시합니다. 기존 settings API에 context_length/thinking_mode/tool_loading만 저장하고 적재된 로컬 모델은 기존 model/load로 재적재합니다. 0=모델 기본값, Thinking 자동/켜기/끄기, 도구 설명은 필요할 때/원본/모두 제공을 선택합니다. 문맥/Thinking은 모델별로 보존하고 작업 중에는 변경을 막습니다. 서버 연결 화면은 로컬 Thinking 스위치를 적용하지 않습니다.

2026-10-18 확인: TypeScript·Vite 빌드 통과. UI 28개 중 서버 적용 순간 연결 거절 1개와 새 검사의 이동 선택자 오류 1개를 수정/재실행해 해당 두 검사가 통과했습니다(나머지 26개는 앞선 실행 통과). 실제 모델 화면에서도 문맥 65536·Thinking auto·도구 lazy 표시와 JavaScript 오류 0건을 확인했습니다. UI 검사는 모의 API이며 실제 채팅/파일 도구 실측은 백엔드 모델 README에 별도 기록합니다.
