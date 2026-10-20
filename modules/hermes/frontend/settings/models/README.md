# 모델 선택과 연결

로컬 GGUF 선택·불러오기·내리기 또는 모델 서버 연결을 담당합니다. 작업 폴더·사용 도구·실행 한도는 별도 작업 환경 소메뉴입니다.

- ModelSettings.tsx: 로컬/서버 공통 탭, 실제 적재 상태와 명령 연결.
- LocalModelPicker.tsx: 이름 검색·모델 선택·파일 경로와 크기 표시. 검색해도 선택을 잃지 않습니다.
- ModelServerForm.tsx: 서버 주소·키·모델 입력. settings 저장 시 연결 필드만 전달합니다.
- CodexModelForm.tsx: ChatGPT · Codex 탭의 로그인 코드·완료 상태·모델 목록과 선택을 담당합니다. 원본 Hermes 인증을 사용하는 codex/status·codex/login·codex/models API에 연결하며 ‘이 모델 사용’에서만 provider/model을 저장합니다. 로그인 토큰은 프론트에 전달하지 않습니다. 실제 첫 응답 완료 전 모델 목록만으로 추론 성공을 표시하지 않습니다.
- 모델은 전체 계정 목록을 공통 Select에 표시합니다. 기존 Input+datalist는 현재 입력값으로 목록을 필터해 GPT-6.1 Sol과 문맥 변형만 보이는 문제가 있었습니다. ReasoningSelect.tsx는 서버가 보낸 모델별 추론 옵션/기본값을 설정 화면과 대화 입력창에서 재사용합니다. 모델명·선택지 배열을 프론트에 고정하지 않고 미지원 실행 모드는 이유와 함께 비활성 표시합니다.
- ../useAgentSettings.ts: 설정 조회·실패 후 다시 불러오기.
- 공통 ui/SettingsSection·Primitives: 패널·읽기 실패·입력·키보드 탭.

모델·추론 선택은 공통 ui-settings-choice-grid로 배치하며 모바일에서는 한 열로 접힙니다. 대화 입력창의 동일한 ReasoningSelect에도 ‘추론’ 이름을 표시합니다. 폰트·색상·간격은 플랫폼 공통 tailwind.css를 사용합니다.

단일 /api의 ai_agent/Hermes/settings, models/local, models, model/load, model/unload에 연결합니다. 화면 이동·검색·모델 선택만으로 로딩·다운로드·실행하지 않습니다. 실제 준비됨은 local_model.state를 따릅니다.

확인: frontend/tests/hermes-workspace.local-browser.spec.ts의 모델 검색·요청 경로·설정 실패 복구 검사. 모델 API는 픽스처로 대체하며 실제 추론을 시작하지 않습니다.

ModelRuntimeControls.tsx는 공통 Input/Select/Button으로 현재 모델의 문맥 한도와 도구 설명 전달 방식을 표시합니다. 기존 settings API에 context_length/tool_loading/max_output_tokens를 저장하고 문맥 한도가 바뀐 경우에만 기존 model/load로 재적재합니다. 출력 한도는 모델별로 저장하고 0은 원본 기본값이며 전체 컨텍스트와 구분합니다. 0=모델 기본값이며 도구 설명은 필요할 때/원본/모두 제공을 선택합니다. 문맥은 모델별로 보존하고 작업 중 변경을 막습니다. Thinking은 [대화 입력창](../../chat/README.md)의 읽기 모드 옆에서 선택하며 모델 화면 저장으로 덮어쓰지 않습니다.

2026-10-18 확인: TypeScript·Vite 빌드와 UI 검사 29개 통과. 모델 실행 설정 저장은 문맥·도구 전달만 보내고, Thinking은 다음 대화 전송에 별도 적용하는 것을 모의 API로 확인했습니다. 실제 채팅/파일 도구 실측은 백엔드 모델 README에 별도 기록합니다.

요청별 최대 출력 토큰은 원본 agent.max_tokens로 전달합니다. 검증에는 8,192를 사용했습니다. 0은 원본 기본값이며 시험 뒤 이전 값으로 복구합니다. 문맥 한도와 Thinking은 바꾸지 않았습니다. 출력 설정만 저장하면 모델을 재적재하지 않습니다.
