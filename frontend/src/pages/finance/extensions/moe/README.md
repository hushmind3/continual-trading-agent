# MoE

- 역할: 화면 컴포넌트와 소속 기능. 
- 핵심 파일: ExpertDiscovery.tsx, ExpertLibraryPanel.tsx, ExpertSearchResult.tsx, ExpertVariants.tsx, ModelFiles.tsx, ModelGuide.tsx, Moe.tsx, PrecisionTolerance.tsx, expertFamilies.ts
- 상위 연결: ../submenu_manager.ts → finance_menu_manager.ts → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 2026-10-14 기존 회귀 검사 및 9개 메뉴 브라우저 탐색 확인. 실제 Expert 추론·양자화·학습은 미실행입니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.

- 주소: `#finance/moe`. 메뉴 등록 ID와 프론트 폴더 이름을 일치시킵니다.

다운로드 버튼은 원본 저장·자동 등록을 수행하고 실제 경로를 표시합니다. 실행기 미확인은 다운로드 차단 조건이 아닙니다. 전체 검사에는 기본 켜진 중복 검사 제외 옵션이 있으며, 선택 버전 삭제는 모델 카드에만 있습니다. 이미 존재하는 정밀도는 재양자화·재검사하지 않습니다. 원본 등록·실행기 미설정 자료는 Frozen 가중치와 구분해 표시합니다.

버튼 연결 수정: 생성은 제거된 종목 선택의 training_symbols를 다시 읽지 않습니다. 패키지 구성 확인·가져오기 요청 실패를 열린 창 안에 표시합니다. 선택 작업 8종·버전 상세·삭제·검색의 요청 및 실패 후 재시도 흐름을 확인했습니다. 실제 생성·Expert 실행 검사·양자화·삭제는 실행하지 않았습니다.

2026-10-14: 등록 JSON에 입력 계약이 없는 Expert도 목록을 표시합니다. 입력 지원 여부를 추정하지 않으며, 손상된 선택값은 기본 선택으로 돌리고 구형 Champion 결과는 표시에서 제외합니다. 실제 모델 파일·등록 JSON은 변경하지 않습니다.

확인 결과(2026-10-14): 수정 전 전체 메뉴 검사에서 MoE 입력 계약 누락으로 화면 전체가 비어짐. 수정 후 백엔드 회귀 검사 32개·API 전송 검사 4개 통과, TypeScript·Vite 빌드 완료, 브라우저 검사 4개 통과(등록 메뉴 9개 탐색 + 입력 계약 누락/손상된 저장값 재현). 기존 모델·등록 JSON은 변경하지 않았습니다.
