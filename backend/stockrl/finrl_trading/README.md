# FinRL-Trading 공통 백엔드

금융 대메뉴가 사용하는 공식 소스와 연결 모듈입니다. 독립 대메뉴·신규 화면은 등록하지 않습니다.

| 폴더 | 역할·진입점 |
| --- | --- |
| price_data/ | operations: 가격 조회·DataStore·DataProcessor·수집 상태; market_storage: 실시간 CSV/일봉 저장 |
| provider_settings/ | operations: 공통 공급원 인증 설정 조회·저장 |
| library/ | 수정하지 않은 공식 FinRL-X 서브모듈 |

__init__.py의 finrlx(name)가 library/finrl_x/에서 공식 모듈을 지연 import합니다. 각 소비 메뉴의 구현이 연결 모듈을 호출하며, 메뉴 등록·단일 API 계층은 유지합니다. React 화면은 frontend/src/pages/finance/에 있습니다.
폴더 이동 완료. 모델·가격·계좌·인증과 공식 알고리즘은 변경하지 않았으며 이번 작업의 실행 검사는 미실행입니다.

## FinRL-X 개입 범위

| 소비 기능 | 연결 파일 | 실제 사용 |
| --- | --- | --- |
| 정책 학습 | finrl/policy_learning/handlers.py, official_cli.py | prices → 공식 DataStore로 등록 종목 가격을 읽어 FinRL/SB3에 전달 |
| 운영·자동 이어 학습 | trading/operation_control/operations_runtime.py | prices로 정책 입력·가격 변경 여부 확인 |
| 키움 등 실시간 시세 저장 | live_feed.py → price_data/market_storage.py | DataProcessor._clean_price_data → DataStore.save_price_data; 원본 CSV·봉 DB 별도 기록 |
| 주식 Expert 입력 | platform/expert_inference.py | price_store의 DB 변경 정보와 prices를 사용해 실제 과거 입력 구성 |
| Expert 조사 | platform/library_operations.py | prices로 입력 가격 제공 |
| 연결·설정 | management/connection_settings/handlers.py | collection_status → 공식 DataFetcher의 공급원 설정 상태 확인 |
| 공급원 설정 | provider_settings/operations.py → management/all_backend_features/handlers.py | config.settings 조회·갱신; 기존 인증 저장소 사용 |
| 원본 함수 수동 실행·모듈 목록 | platform/framework_operations.py | 선택한 FinRL-X 모듈 동적 import, $config, 원본 파일 목록·호출 기록 |
| 실행 프로세스·설치 | platform/system_operations.py, development/scripts/install_windows.py | 공급원 환경 전달, 공식 import 상태 표시, 고정 서브모듈 설치 |

직접 원본 호출은 price_data/operations.py, provider_settings/operations.py와 원본 함수 실행 도구에 모았습니다. 다른 기능은 명시적 연결 함수를 import합니다. 중앙 api_context의 finrlx 재노출은 제거했습니다.

## 분리 결과와 제한

- 흩어져 있던 market_storage.py를 price_data/로 실제 이동했습니다. 원본 함수·청소 규칙·가격 처리 동작은 유지합니다.
- 설치 요구사항은 development/scripts/requirements/finrl_trading.txt로 분리했습니다. operations.txt가 포함하며 기존 버전·공유 환경·잠금 파일은 유지합니다. 추가 설치·삭제는 하지 않았습니다.
- 이 단계는 코드·설치 명세 경계를 분리한 것입니다. **FinRL-X 없는 실행은 아직 불가능합니다.** 현재 중앙 학습·실시간 일봉 저장·일부 Expert 입력이 DataStore/DataProcessor에 필수 의존합니다.
- FinRL/SB3의 알고리즘·정책·환경은 FinRL-X로 교체되지 않습니다. FinRL-X 전략·백테스트·매매·ML 코드는 원본 함수 도구에서 선택 가능한 소스이며, 정적 참조만으로 실제 실행을 단정하지 않습니다.
- REA 자체 소스에는 FinRL-X import가 없습니다. 플랫폼 공통 실행 환경은 공유합니다.
- 원본은 library/finrl_x/이며 커밋은 4409abe925c904e570be78ebfb5e77ac3491dff8입니다. 공식 원본·모델·가격 DB·계좌·인증·로컬 설정은 변경하지 않았습니다.
- 사용처 조사는 정적 import·호출 소스에 근거합니다. 학습·추론·수집·진단 검사는 미실행입니다.
