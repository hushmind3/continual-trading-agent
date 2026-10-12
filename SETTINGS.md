# 공식 기본값과 현재 연결 설정

이 문서는 현재 `main`의 실행 경로에서 프레임워크 원본, 공식 예제 설정, 프로젝트 연결 설정을 구분한다. "공식 기본값"이라고 부를 수 있는 범위는 설치된 라이브러리 기본값 또는 호출하는 공식 예제에 실제 적힌 값뿐이다.

## SAC 학습

| 설정 | 현재 값 | 출처 |
|---|---:|---|
| 학습 함수 | FinRL `DRLAgent.get_model()` / `DRLAgent.train_model()` | `backend/stockrl/finrl/framework.py`의 현재 호출 |
| 알고리즘 / 정책 | SB3 `SAC`, `MlpPolicy` | FinRL `DRLAgent.get_model()` 기본 정책 및 SB3 원본 |
| 기본 학습 단계 | 5,000 | 설치된 FinRL `DRLAgent.train_model(total_timesteps=...)` 기본값. 요청의 `total_timesteps`로 변경 가능 |
| 배치 크기 | 64 | 설치된 FinRL `MODEL_KWARGS['sac']` |
| Replay 용량 | 100,000 | 설치된 FinRL `MODEL_KWARGS['sac']` |
| 학습률 | 0.0001 | 설치된 FinRL `MODEL_KWARGS['sac']` |
| 학습 시작 전 단계 | 100 | 설치된 FinRL `MODEL_KWARGS['sac']` |
| 엔트로피 계수 | `auto_0.1` | 설치된 FinRL `MODEL_KWARGS['sac']` |
| 그 밖의 SAC 인자 | SB3 설치 버전의 기본값 | 호출부에서 별도 인자를 넘기지 않음 |
| Actor / Critic MLP | `[256, 256]`, ReLU | SB3 SAC 정책 기본값 |
| 장치 | `auto` | SB3 기본값. 라이브러리가 CUDA 사용 가능 여부로 선택 |

위 다섯 SAC 인자는 **SB3 라이브러리 기본값 전체가 아니라 설치된 FinRL의 알고리즘 설정**이다. SB3 SAC 자체 기본값은 배치 256, Replay 1,000,000, 학습률 0.0003, 엔트로피 `auto`이며 `state.settings.sb3_defaults`에서 별도로 조회한다. FinRL-X의 과거 `train_sac` 예제 설정을 현재 주 학습 경로로 설명하지 않는다. SB3의 학습·손실·Optimizer·Replay를 사용하되, SAC 및 MoE Champion의 관측 결합에는 프로젝트 `ChampionExtractor`를 연결한다.

이 프로젝트는 정상 학습 종료 후 공식 SB3 `save()`와, Replay를 지원하는 알고리즘의 `save_replay_buffer()`를 호출한다. A2C/PPO는 Replay를 저장하지 않는다. 자체 중간 저장 주기는 추가하지 않았다. 이어 학습은 동일 알고리즘·환경·통화·종목·Expert 계약을 검사하며 구형 환경의 정책·Replay를 자동 변환하지 않는다. MoE 생성과 학습은 설치된 FinRL의 A2C/DDPG/PPO/TD3/SAC/TQC/CrossQ 목록을 사용하며 정책 구조와 Replay 지원 여부를 알고리즘별로 구분한다.

## 가격·전처리·환경

| 설정 | 현재 값 | 출처 / 의미 |
|---|---:|---|
| 가격 저장·조회 | FinRL-X `DataStore` | 원본 FinRL-X API |
| 정책 가격 전처리 | `normalize_df='by_previous_time'` | `PortfolioOptimizationEnv` 원본 기본값. 별도 StockTradingEnv 화면은 `FeatureEngineer` 사용 |
| 학습·평가 구간 나누기 | FinRL `data_split()` | `training_environment()`에서 원본 함수 호출 |
| rolling 시작 범위 / 평가 구간 | 1,095일 / 365일 | 프로젝트가 마지막 가격 다음 날을 기준으로 학습 종료·평가 시작을 계산 |
| 포트폴리오 환경 | FinRL `PortfolioOptimizationEnv` + Shimmy + `ExpertObservation` | `cash_environment()`의 현재 환경 |
| 공분산 lookback | 사용하지 않음 | 현재 환경에 공분산 관측을 추가하지 않음 |
| `hmax` | 사용하지 않음 | 현재 환경의 인자가 아님 |
| 초기 자본 | 1,000,000 | 프로젝트 환경 생성 시 지정 |
| 수수료 | `comission_fee_model='trf'`, `comission_fee_pct=0` | 환경 원본 기본값. 운영 가상계좌의 수수료·슬리피지와 별도 |
| `reward_scaling` | 1 | 환경 원본 기본값 |
| 관측 / 행동 | 가격 관측을 펼친 값 + Expert별 64D + 계좌 16D / 현금 1 + 종목 수 | 현금은 환경 행동의 첫 항목이며 원장 전달 시 마지막 항목으로 이동 |
| 가격 특성 | `close`, `high`, `low` | 환경 원본 `features` 기본값 |
| 관측 시간창 | `time_window=1` | 환경 원본 기본값 |

현재 주 정책 경로는 FinRL의 현금 포함 `PortfolioOptimizationEnv`다. 과거 `StockPortfolioEnv`의 관측·행동 규격과 다르며 구형 체크포인트는 호환 검사에서 차단한다. 원본의 Gym 환경은 Shimmy로 Gymnasium 계약에 연결하고 가격 행렬의 날짜별 종목 누락·중복을 학습 전에 검사한다. 별도 주식거래 메뉴의 `StockTradingEnv` 결과를 MoE Champion과 호환이라고 표시하지 않는다.

환경의 가격 정규화·보상·수수료 동작은 설치된 `PortfolioOptimizationEnv` 원본을 따른다. 학습 환경과 운영 `PaperAccount`의 체결·비용 계산은 별도이며 실제 증권사 주문을 실행하지 않는다. 정책 백테스트는 원본 환경의 비중을 FinRL-X `StrategyResult`·`BacktestEngine`에 전달한다.

## Expert 연결과 프로젝트 전용 값

Expert는 동결 자산이며 등록·선택·로딩·해제는 프로젝트 연결 계층이 담당한다. Expert를 학습시키거나 Expert 구조에 SAC 설정을 덮어쓰지 않는다. Gymnasium `ObservationWrapper`는 기존 환경 관측 뒤에 Expert별 실제 출력 64D와 계좌 상대값 16D를 붙인다. `ChampionExtractor`는 이 입력을 공식 알고리즘의 정책·가치 구조에 연결한다. 이는 FinRL-X/SB3 원본 기본 구조가 아니라 프로젝트 관측 계약이다.

현재 코드에는 프레임워크 기본값이 아닌 Expert 연결 값도 있다.

| 설정 | 현재 값 | 범위 |
|---|---:|---|
| Expert 출력 | Expert별 64D + 계좌 16D | 프로젝트 관측 계약 |
| 예측 요청 기본 horizon | 1 | 프로젝트 호출 계약; 최대 요청 128 |
| 최소 시장 이력 | 예측형 32행, 매매형 128행 | Expert 등록 계약 |
| Expert 결과 캐시 | Expert·통화별 마지막 입력·계좌 서명과 결과 | `ExpertRegistry.outputs()`가 동일 입력일 때 재사용하며 새 입력으로 교체 |
| 메모리 여유 예약 | 없음 | 현재 사용 가능 RAM/VRAM 기준 |
| Expert 요청 제한 시간 | HTTP 라이브러리 기본값 | 요청 timeout 인자 생략 |
| Native Expert Torch CPU threads | PyTorch 기본값 | 별도 전역 재설정 제거 |
| Native Expert seed | 라이브러리 난수 기본 상태 | 별도 전역 seed 재설정 제거 |
| Chronos 샘플 수 | Chronos API 기본값 | `num_samples` 인자 생략 |
| EXAONE 예측 batch 크기 | EXAONE API 기본값 | `batch_size` 인자 생략 |
| Kronos context / sample count / verbosity | Kronos API 기본값 | 선택 인자 생략 |
| GGUF 포트·로그 경로 | 동적 포트·전용 로그 파일 | 여러 Expert 프로세스 연결 |

메모리 예약을 임의로 추가하지 않고 현재 사용 가능 메모리로 적재를 판단한다. Expert 출력 캐시와 통합 관리자의 정책·메타데이터 캐시는 역할이 다르다. Expert 입출력 계약을 유지하면서 라이브러리가 기본값을 제공하는 선택 인자는 생략하며 horizon, 장치, 모델 가중치 형식, 입출력 tensor dtype처럼 패키지 호환에 필요한 인자는 유지한다.

공식 설정과 프로젝트 연결 설정을 적용할 때의 기준은 다음과 같다.

- 공식 라이브러리 인자가 있으면 해당 공식 함수의 기본값 또는 선택한 공식 예제값을 사용한다.
- Expert 패키지 호환에 필요한 값은 해당 모델 계약으로 유지한다. 이를 FinRL-X의 기본값이라고 부르지 않는다.
- 공식 원본 둘 사이에 API 차이가 있으면 그 차이를 문서화한다. 원본 파일을 고치거나 임의 설정으로 같다고 가장하지 않는다.
- 새 모델 계약과 기존 Expert 입력·출력 호환성은 별도 변경으로 취급한다.

## GGUF / llama.cpp

GGUF 실행은 설치된 `llama-server`를 사용한다. 컨텍스트 길이, CPU 스레드, GPU 레이어, 메모리 맞춤, RAM 캐시, 병렬 슬롯, 샘플링 온도, seed, 생성 토큰 수, thinking 옵션을 실행 명령이나 요청에 강제로 넣지 않는다. llama.cpp와 GGUF 모델이 제공하는 기본값을 따른다. 프로젝트는 포트와 로그 경로만 연결에 사용한다.

## 현재 범위와 검증 상태

- 학습 입력은 FinRL-X `DataStore`에 저장된 과거 가격이다.
- FinRL-X의 `StrategyResult`와 `BacktestEngine` 원본 API를 호출한다.
- 학습·백테스트는 저장 가격을 사용한다. 운영 시세 수신은 별도 Yahoo/Kraken/키움 경로이며 실제 증권사 주문은 호출하지 않는다.
- 2026-10-13 현재 선택된 11개 Expert, AAPL/MSFT·USD·SAC로 신규 모델 생성과 105단계 진단 학습(업데이트 5회)을 실제 실행했다. 기본 5,000단계를 변경한 것이 아니며 수익성·수렴 검증이 아니다. 관측 726D와 현금 포함 행동 3D를 확인했다.
- 원본 FinRL-X 서브모듈 소스는 수정하지 않는다.

## 원본 위치

- FinRL-X 서브모듈 커밋: `4409abe925c904e570be78ebfb5e77ac3491dff8`
- FinRL 설치 소스 커밋: `00f3596facd01cced5217d875d8c1fc413a31665`
- 현재 알고리즘 설정·기본 단계: 설치된 `finrl/agents/stablebaselines3/models.py`
- 과거 SAC 예제: `FinRL-X/src/strategies/rl_model.py` (현재 주 학습 경로 아님)
- rolling 예제 설정: `FinRL-X/src/strategies/fundamental_portfolio_drl.py`
- 포트폴리오 환경: 설치된 `finrl/meta/env_portfolio_optimization/env_portfolio_optimization.py`
- SB3 SAC 기본 정책: 설치된 `stable_baselines3/sac/policies.py`, `stable_baselines3/sac/sac.py`

## 실행 의존성

운영/키움 요구와 재현 버전은 `requirements/operations.txt`, `operations.lock.txt`, `kiwoom.txt`, `kiwoom.lock.txt`가 관리합니다. `.venv`는 websockets 10.4, `.venv-kiwoom`은 SDK 1.0.2와 websockets 15.0.1을 사용합니다. 주 FinRL/NumPy/Pandas 버전을 SDK 요구에 맞춰 바꾸지 않습니다. `teachers`의 stockstats도 FinRL 요구와 같은 0.5.4입니다. Frozen FinCast의 실제 실행 의존성 beartype 0.22.9/einx 0.4.3/colt5-attention 0.11.2를 포함합니다.

원본 주식 Expert는 전체 학습 종목의 동일 과거 거래일 가격·원본 지표를 요구합니다. 일부 종목만 갱신된 최근 일봉 대신 관측 시점 이전의 가장 최근 완전한 공통 거래일을 사용합니다. 일봉을 만들거나 종목을 제외하지 않습니다.

2026-10-13 실행 검증: 신규 SAC의 11개 Expert 모두 CUDA 추론, 105단계 진단 학습·업데이트 5회, 평가 251개 거래일과 공식 가치·지표 저장을 완료했습니다. 현재 USD 선택은 새 호환 체크포인트이며 구형 모델·Replay와 이전 선택 경로는 보존합니다. 원본 BacktestEngine의 가중치 이력·거래 DataFrame은 비어 있으므로 해당 표를 체결 내역으로 취급하지 않습니다.
