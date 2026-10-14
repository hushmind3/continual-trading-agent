# 운영 제어

- 역할: menu.py: 메뉴 등록; handlers.py: 기존 API 처리. 
- 핵심 파일: handlers.py, menu.py, operations_runtime.py, operations_settings.py
- 상위 연결: ../submenu_manager.py → finance_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.

프론트 메뉴 주소: `#finance/operation_control`; 화면: `frontend/src/pages/finance/trading/operation_control/OperationControl.tsx`. 백엔드 폴더·import 이름은 프론트 소메뉴 폴더와 일치합니다. API 작업명은 유지합니다.

Expert 모델 설정 경로는 operations_settings.settings().model_dir 및 registry_file에서 제공합니다. 실제 등록·선택 정보는 바탕화면 모델/experts/expert_registry.json과 각 모델 폴더의 expert.json에 있습니다. 프로젝트 configs/experts.json을 읽지 않습니다.

2026-10-14: 가상주문에서 NaT/누락 시각, 0·누락·NaN·무한 가격, 잘못된 호가를 원장 변경 전에 거부합니다. 통화 목록과 종목·장치 설정 자료형을 저장/실행 전에 확인합니다. 임시 계좌·설정 및 가짜 실행기로 검사했으며 알고리즘·수수료·슬리피지 기본값은 변경하지 않았습니다.

주기 연결: 운영 판단과 지속학습은 dataset.json의 timeframe(구형 현재 환경 기록은 training_input.timeframe, 누락 시 기존 1d)을 따릅니다. 1m 정책은 완료된 분봉이 저장될 때 입력이 바뀌며, 요청 작업과 결과도 같은 주기를 유지해야 운영에 반영합니다. 기존 일봉 정책을 자동으로 분봉 정책으로 바꾸지 않습니다. 최신 수정 후 실제 시세·판단·학습·가상체결 검사는 미실행입니다.

소비 범위 연결: 데이터 지문이 같아도 consumed_end 뒤의 미소비 봉이 남아 있으면 다음 학습 작업을 요청합니다. 성공한 작업 종료도 처리 신호로 사용해 새 시세가 오지 않는 동안 남은 입력을 이어갈 수 있습니다. 실제 소비 시각·전이 수가 없거나 범위가 잘못됐거나 새 봉을 소비하지 않은 결과는 운영 반영하지 않습니다. 이미 소비한 동일 입력은 대기 목록에서 제거합니다. 알고리즘 단계 수·업데이트 비율을 자동 조절하는 기능과 실제 동작 검증은 아직 미완료입니다.

키움 SDK 작업 종료 시 전체·국내·미국 연결 표시를 함께 종료합니다. 수신 제어가 켜진 동안 비정상 작업 종료는 2~60초 간격으로 재연결하며 중지는 대기를 취소합니다. 운영 화면에 실제 연결·재연결·가격 이벤트 수·최근 시세 시각을 별도로 표시합니다. 국내 구독/거래소 수신 통계를 공통 상태에 전달합니다.

실제 수신 버튼 실행에서 latest_quotes 초기화 누락을 확인하여 LiveMarketCollector 생성 시 가격 이벤트 저장소를 준비하도록 수정했습니다. 학습·자동 판단·가상매매는 켜지 않았습니다.

실제 확인: 초기화 수정 후 수신 버튼으로 미국 연결 true·가격 이벤트 25건을 받았습니다. 국내 연결 false·ConnectionClosedOK(Bye)로 국내 수신은 미완료입니다. 확인 후 모든 운영 제어를 끄고 체결 증가 0건을 확인했습니다.

자동 운영 시작은 사용자 선택 정책 로드 → 시세 수신 → 가상매매·정책 판단·지속학습을 함께 활성화합니다. 개별 실행 UI는 제거했습니다. 중지는 네 기능을 함께 끕니다. 선택 정책이 한 통화에만 있으면 화면 기본 선택도 해당 통화이며 신규 모델 자동 생성·원본 Expert 학습은 수행하지 않습니다.
