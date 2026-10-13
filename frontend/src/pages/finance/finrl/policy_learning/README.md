# 정책 학습

- 주소: #finance/policy_learning. PolicyLearning.tsx → PolicyTrainingControls.tsx, JobLog, CheckpointPanel.
- 원화(KRW)·달러(USD) 학습 카드를 동시에 표시합니다. USD 단일 기본 선택 및 종목 선택·목록 UI는 없습니다.
- 학습 요청은 해당 통화에 등록된 학습 대상 종목 전체를 명시적으로 전달합니다. 저장 가격이 없는 종목을 조용히 제외하거나 선택한 Champion의 종목으로 바꾸지 않습니다.
- 알고리즘별 FinRL MODEL_KWARGS 및 설치된 SB3 생성자 기본값은 algorithms 읽기 API로 확인합니다. 공식 알고리즘·설정값은 수정하지 않습니다.
- 통화별 실행 전 검사·학습·Champion 선택은 사용자의 버튼 조작으로만 실행합니다. 새 정책·Champion 생성·학습을 자동 호출하지 않습니다.
- 상위 연결: finrl/submenu_manager → 금융 매니저 → 전체 메뉴 매니저 → 단일 /api. backend/stockrl/finrl/policy_learning/handlers.py가 기존 요청을 처리합니다.
- 오래된 SAC 전용 구조·단일 통화 준비 화면은 의존성 확인 후 휴지통으로 옮겼습니다. 정책·가격·계좌 데이터는 변경하지 않았습니다.
