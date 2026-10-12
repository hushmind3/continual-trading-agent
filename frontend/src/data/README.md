# 단일 API·공통 상태

| 파일 | 역할 |
| --- | --- |
| api.ts | /api 전송과 같은 통로의 다운로드 URL |
| Operations.tsx | OperationsProvider: 통합 state 조회·구독·명령·갱신 |
| types.ts | 백엔드 응답과 구역 타입 |
| library.ts | 기존 라이브러리 작업 연결 |

- 상태는 Provider가 한 번에 조회하며 화면은 공통 상태를 구독합니다.
- 버튼은 기존 operation과 payload를 execute로 전달합니다.
- Python 모듈은 프론트에서 import하지 않습니다.
- API 계약과 상태 의미를 화면 변경 때문에 임의로 바꾸지 않습니다.

menu_types.ts는 메뉴·추가 작업·API 입력 계약 응답 타입입니다. menu_catalog는 상태 Provider의 동일 요청에 포함됩니다. API 전송기는 명시적인 GET 조회와 POST 실행을 구분합니다.

BackendAction.menu_id는 담당 작은 메뉴이며 추가 입력 허용 여부는 API의 additionalProperties 계약을 사용합니다.

OperationsProvider의 algorithm/selectAlgorithm은 학습·MoE가 공유하는 선택값이며 세션에 유지합니다. Champion 응답은 identity.algorithm과 policy_spaces를 사용합니다.
