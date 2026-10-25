# 공용 추론 선택기

용도: 기존 대화 입력창의 모델별 추론 수준 표시를 공유합니다.

- `ReasoningSelect.tsx`: ChatComposer·ThinkingControl·useThinking이 사용하는 선택기와 타입입니다.
- 실제 모델 관리 화면은 ../official/OfficialWorkspace.tsx와 공식 ModelsPage입니다. 구형 ModelSettings·연결 폼·모델 목록 화면은 공식 기능으로 교체 후 휴지통으로 옮겼습니다.
- 설정·인증·모델 목록은 기존 /api와 공식 실행 설정을 기준으로 하며 선택지를 모델 이름에 맞춰 임의 하드코딩하지 않습니다.
