# 저장 가격 조회

- 핵심 파일·진입점: operations.py의 prices(currency, symbols).
- 사용처: 금융 policy_learning, trading/operation_control 및 platform의 공식 함수 실행·Expert 추론.
- 필수 의존성: 상위 finrlx → 공식 data.data_store, pandas, SQLite, stockrl.ROOT.
- 보호 대상: 기존 data/·runtime/ 가격 자료를 그대로 사용합니다.
- 상태: import 경로 재배치 완료. 실제 학습·추론·가격 조회 검사는 미실행입니다.
