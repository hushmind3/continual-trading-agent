# 모델과 추론 설정

용도: 대화·총괄의 주 모델 선택과 모델별 추론 수준을 관리합니다.

- `ModelSettings.tsx`: 원본 ModelPickerDialog를 재사용해 연결된 제공자와 `ai_agent/choki/models/local`에서 찾은 실제 GGUF를 함께 고릅니다. 로컬 목록은 파일 크기와 모델 루트 기준 상대 경로를 표시해 같은 이름도 구분하고, 선택된 파일의 실제 경로를 settings API와 `model/load`에 전달합니다. ChatGPT 목록은 실제 계정 카탈로그로 제한합니다.
- `ReasoningSelect.tsx`: 모델이 광고한 추론 수준과 전송 지원 여부를 표시합니다. 낮음은 가벼운 추론이며 모델 화면의 선택은 기존 settings API에 저장하고 대화 입력창도 같은 설정을 사용합니다.
- 보조 모델·여러 모델 협업은 고급 모델 설정에서 원본 화면을 그대로 엽니다. 계정·서비스 인증도 기존 원본 화면을 사용합니다.
- 연결: ../../types.ts의 단일 API 접두사, `settings`, `models/local`, `model/load`, ../../chat/useThinking.ts, ../official/transport.ts, ../../agent_navigation.ts.
- 확인: 플랫폼 TypeScript·Vite 빌드 후 기존 대화의 모델 버튼과 설정 화면에서 실제 제공자·카탈로그·추론 수준을 확인합니다. 목록 조회를 전체 제공자의 실제 추론 성공으로 기록하지 않습니다.
