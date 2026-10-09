# 공식 기본값과 현재 연결 설정

이 문서는 현재 `main`의 실행 경로에서 프레임워크 원본, 공식 예제 설정, 프로젝트 연결 설정을 구분한다. "공식 기본값"이라고 부를 수 있는 범위는 설치된 라이브러리 기본값 또는 호출하는 공식 예제에 실제 적힌 값뿐이다.

## SAC 학습

| 설정 | 현재 값 | 출처 |
|---|---:|---|
| 학습 함수 | `FinRL-X/src/strategies/rl_model.py::train_sac(agent)` 직접 호출 | FinRL-X 원본 함수 |
| 알고리즘 / 정책 | SB3 `SAC`, `MlpPolicy` | FinRL `DRLAgent.get_model()` 기본 정책 및 SB3 원본 |
| 총 학습 단계 | 50,000 | FinRL-X `train_sac` 예제 |
| 배치 크기 | 128 | FinRL-X SAC 예제에서 지정 |
| Replay 용량 | 100,000 | FinRL-X SAC 예제에서 지정 |
| 학습률 | 0.0003 | FinRL-X SAC 예제에서 지정 |
| 학습 시작 전 단계 | 100 | FinRL-X SAC 예제에서 지정 |
| 엔트로피 계수 | `auto_0.1` | FinRL-X SAC 예제에서 지정 |
| 그 밖의 SAC 인자 | SB3 설치 버전의 기본값 | 호출부에서 별도 인자를 넘기지 않음 |
| Actor / Critic MLP | `[256, 256]`, ReLU | SB3 SAC 정책 기본값 |
| 장치 | `auto` | SB3 기본값. 라이브러리가 CUDA 사용 가능 여부로 선택 |

위 다섯 SAC 인자는 **SB3 라이브러리 기본값 전체가 아니라 FinRL-X 공식 예제의 값**이다. 예제를 그대로 실행하는 경로에서는 예제 값을 바꾸지 않는다. 별도로 만든 정책 구조, 손실 함수, Optimizer, Replay 구현은 사용하지 않는다.

FinRL-X 예제는 학습 종료 시점 체크포인트를 만들도록 정하지 않는다. 이 프로젝트는 재시작을 위해 공식 SB3 `save()`와 `save_replay_buffer()`를 학습 종료 후 호출한다. 자체 중간 저장 주기나 자체 학습 반복 횟수는 추가하지 않았다. 이전 프로젝트 자체 정책과 Replay는 새 SAC 정책에 승계하지 않는다.

## 가격·전처리·환경

| 설정 | 현재 값 | 출처 / 의미 |
|---|---:|---|
| 가격 저장·조회 | FinRL-X `DataStore` | 원본 FinRL-X API |
| 기술 지표 전처리 | FinRL `FeatureEngineer()` | 원본 생성자 기본 설정 |
| 학습·평가 구간 나누기 | FinRL-X `prepare_rolling_train/test()` | 원본 함수 |
| 전체 rolling 구간 / 평가 구간 | 1,095일 / 365일 | FinRL-X `fundamental_portfolio_drl.py` 예제 호출값 |
| 포트폴리오 환경 | FinRL `StockPortfolioEnv` | 설치된 FinRL 원본 클래스 |
| 공분산 lookback | 252 거래 관측 | FinRL Portfolio Allocation 튜토리얼 방식 |
| `hmax` | 100 | FinRL Portfolio Allocation 튜토리얼 값 |
| 초기 자본 | 1,000,000 | FinRL Portfolio Allocation 튜토리얼 값 |
| `transaction_cost_pct` | 0.001 | FinRL Portfolio Allocation 튜토리얼 값 |
| `reward_scaling` | 0.0001 | FinRL Portfolio Allocation 튜토리얼 값 |
| 종목·상태·행동 차원 | 선택 종목 수 | 이 환경의 포트폴리오 입력 규격 |
| 지표 목록 | `finrl.config.INDICATORS` | 설치된 FinRL 설정 |
| `turbulence_threshold`, `lookback`, `day` | `None`, 252, 0 | 원본 생성자 기본값 |

환경은 FinRL-X가 아니라 FinRL의 공식 `StockPortfolioEnv`다. FinRL-X `fundamental_portfolio_drl.py`의 환경 설정 전체를 그대로 쓴다고 표시하면 틀린다. 그 예제는 `k_eig=10`을 전달하지만 설치된 FinRL `StockPortfolioEnv`에는 `k_eig` 인자가 없다. 현재 연결은 별도 `k_eig`나 임의 환경 변경 없이 FinRL의 Portfolio Allocation 튜토리얼 입력 규격을 사용한다.

환경의 원본 `step()`은 행동을 합계 1의 포트폴리오 비중으로 정규화하고 다음 가격 변화로 계좌 가치를 계산한다. 원본 코드에서 `transaction_cost_pct`는 이 `step()`에 적용되지 않으며 `reward_scaling`도 보상 계산에서 주석 처리되어 있다. 따라서 이 환경을 실제 수수료 차감 체결이나 실계좌 동작으로 설명하지 않는다. 별도의 FinRL-X `BacktestEngine`은 엔진 원본 기본 설정으로 실행하며, 자체 설정을 넘기는 경우 시작일과 종료일만 지정한다.

## Expert 연결과 프로젝트 전용 값

Expert는 동결 자산이며 등록·선택·로딩·해제는 프로젝트 연결 계층이 담당한다. Expert를 학습시키거나 Expert 구조에 SAC 설정을 덮어쓰지 않는다. 관측 연결은 Gymnasium `ObservationWrapper`를 사용하며, 기존 환경 관측 뒤에 시장 예측·매매 판단의 요약 신호 8개를 붙인다. 이는 FinRL-X/SB3 기본 기능이 아니라 현재 Expert 입력 계약이다.

현재 코드에는 프레임워크 기본값이 아닌 Expert 연결 값도 있다.

| 설정 | 현재 값 | 범위 |
|---|---:|---|
| Expert 출력 요약 | 8개 값 | 프로젝트 관측 계약 |
| 예측 요청 기본 horizon | 1 | 프로젝트 호출 계약; 최대 요청 128 |
| 최소 시장 이력 | 예측형 32행, 매매형 128행 | Expert 등록 계약 |
| Expert 결과 캐시 상한 | 제한 없음 | 별도 캐시 제한 제거 |
| 메모리 여유 예약 | 없음 | 현재 사용 가능 RAM/VRAM 기준 |
| Expert 요청 제한 시간 | HTTP 라이브러리 기본값 | 요청 timeout 인자 생략 |
| Native Expert Torch CPU threads | PyTorch 기본값 | 별도 전역 재설정 제거 |
| Native Expert seed | 라이브러리 난수 기본 상태 | 별도 전역 seed 재설정 제거 |
| Chronos 샘플 수 | Chronos API 기본값 | `num_samples` 인자 생략 |
| EXAONE 예측 batch 크기 | EXAONE API 기본값 | `batch_size` 인자 생략 |
| Kronos context / sample count / verbosity | Kronos API 기본값 | 선택 인자 생략 |
| GGUF 포트·로그 경로 | 동적 포트·전용 로그 파일 | 여러 Expert 프로세스 연결 |

메모리 예약·캐시 상한을 임의로 제한하지 않고 현재 사용 가능 메모리로 적재를 판단한다. Expert 입출력 계약은 유지하면서 라이브러리가 기본값을 제공하는 선택 인자는 생략한다. horizon, 장치, 모델 가중치 형식, 입출력 tensor dtype처럼 패키지 호환에 필요한 인자는 유지한다.

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
- 현재 이 경로는 키움 실시간 수신과 실제 주문을 실행하지 않는다.
- 50,000단계 공식 SAC 예제 학습을 이번 변경 과정에서 실행하지 않았다. 따라서 완료된 학습이나 수익률 개선을 주장하지 않는다.
- 원본 FinRL-X 서브모듈 소스는 수정하지 않는다.

## 원본 위치

- FinRL-X 서브모듈 커밋: `4409abe925c904e570be78ebfb5e77ac3491dff8`
- FinRL 설치 소스 커밋: `00f3596facd01cced5217d875d8c1fc413a31665`
- SAC 예제: `FinRL-X/src/strategies/rl_model.py`
- rolling 예제 설정: `FinRL-X/src/strategies/fundamental_portfolio_drl.py`
- 포트폴리오 환경: 설치된 `finrl/meta/env_portfolio_allocation/env_portfolio.py`
- SB3 SAC 기본 정책: 설치된 `stable_baselines3/sac/policies.py`, `stable_baselines3/sac/sac.py`
