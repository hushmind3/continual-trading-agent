# 스크립트 찾기

프로젝트 루트에서 실행합니다. 일반 운영은 루트 `설치.cmd`와 `서버켜기.cmd`를 사용합니다.

| 용도 | 파일 |
| --- | --- |
| Windows 설치 | `install_windows.py` |
| Python API / Vite 시작 | `start_local.ps1` |
| 과거 데이터 MoE 실행 도구 | `run_native_vertical_trading.py` |
| 단독 추론·가상매매 도구 | `run_trading_moe.py`, `run_trading_moe_paper.py` |
| 모델 패키징·주식 전문가 추가 | `package_trading_moe.py`, `add_stock_policy_experts.py` |
| Native 입력 준비 | `prepare_native_moe_inputs.py` |
| 원본 전문가 검증·보고서 | `audit_frozen_experts.py`, `verify_frozen_experts.py`, `verify_trading_moe_integration.py` |
| 데이터 수집·변환 | `download_*`, `ingest_*`, `fetch_fi2010.py`, `parse_nasdaq_itch_sample.py` |
| 실행 상태 보존 | `snapshot_runtime.py` |

실시간 운영은 `src/stockrl/platform`을 사용합니다. 단독 추론·과거 데이터 도구는 운영 프로세스와 별도로 실행합니다.
