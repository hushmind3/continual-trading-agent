# 스크립트 찾기

프로젝트 루트에서 실행합니다. 일반 운영은 루트 `설치.cmd`와 `서버켜기.cmd`를 사용합니다.

| 용도 | 파일 |
| --- | --- |
| Windows 설치 | `install_windows.py` |
| TradingMoE 연속 worker | `run_native_vertical_trading.py` |
| 자동조립 paired 평가 worker | `run_assembly_trial.py` |
| 단독 추론·가상매매 도구 | `run_trading_moe.py`, `run_trading_moe_paper.py` |
| 모델 패키징·주식 전문가 추가 | `package_trading_moe.py`, `add_stock_policy_experts.py` |
| Native 입력 준비 | `prepare_native_moe_inputs.py` |
| 원본 전문가 검증·보고서 | `audit_frozen_experts.py`, `verify_frozen_experts.py`, `verify_trading_moe_integration.py` |
| 데이터 수집·변환 | `download_*`, `ingest_*`, `fetch_fi2010.py`, `parse_nasdaq_itch_sample.py` |
| 실행 상태 보존·용량 정리 | `snapshot_runtime.py`, `compact_project.ps1` |

구형 0.5B 실행기, 해당 모델 전용 데이터 변환기와 미사용 teacher 사전검사 스크립트는 프로젝트 외부 휴지통으로 옮겼습니다. 저장 경험을 읽기 위한 `stockrl.online` 호환 경로는 기존 replay 복구에 필요해 유지합니다.
