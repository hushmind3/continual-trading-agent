# FinRL-X · 공식 SAC + 동결 Expert

FinRL-X와 FinRL, Stable-Baselines3의 원본 모듈을 호출합니다. 학습 신경망이나 알고리즘을 별도로 구현하지 않습니다. 공식 라이브러리 기본값, FinRL-X 예제 설정, Expert 호환 설정의 구분은 [SETTINGS.md](SETTINGS.md)에 기록했습니다.

## 실제 구성

| 영역 | 사용하는 원본 |
| --- | --- |
| 가격 저장·조회 | FinRL-X `DataStore` |
| 기술 지표 | FinRL `FeatureEngineer` |
| 포트폴리오 가치 환경 | FinRL `StockPortfolioEnv` 원본 |
| Actor·Twin Critic·Target Critic | SB3 기본 `SACPolicy / MlpPolicy` |
| SAC·Adam·Loss·Replay | SB3 `SAC` 기본 구현 |
| 저장·복원 | SB3 `save/load`, `save_replay_buffer/load_replay_buffer` |
| 전략 출력·백테스트 | FinRL-X `StrategyResult / BacktestEngine` |
| 화면 | f153957 React 디자인 복원 · Vite · TypeScript · Tailwind CSS · TanStack Table |

공식 소스는 [FinRL-X](https://github.com/AI4Finance-Foundation/FinRL-Trading) 서브모듈과 설치된 [FinRL](https://github.com/AI4Finance-Foundation/FinRL), [SB3](https://stable-baselines3.readthedocs.io/en/master/modules/sac.html)입니다. `FinRL-X` 파일은 수정하지 않습니다.

## 학습 설정

FinRL-X `src/strategies/rl_model.py`의 원본 `train_sac(agent)`를 직접 호출합니다.

```python
batch_size = 128
buffer_size = 100000
learning_rate = 0.0003
learning_starts = 100
ent_coef = "auto_0.1"
```

나머지는 SB3 기본값입니다. 중앙 신경망은 기본 `[256, 256]` 구조이고 `device="auto"`가 현재 PC에서 CUDA를 선택합니다. 기존 중앙 신경망·Optimizer·Replay는 승계하지 않습니다. 새 정책과 Replay는 `runtime/official`에 저장합니다. 같은 종목 구성에서는 해당 정책을 공식 `load()`로 이어 학습할 수 있습니다. 실행 단계 수는 원본 예제의 50,000단계입니다. 원본 예제에 없는 1,000단계 주기 체크포인트와 자체 logger 설정을 제거했습니다. 모델과 Replay는 실행 종료 시 저장합니다. 기존 다른 설정으로 만든 정책은 이어 학습하지 않습니다.

환경은 설치된 원본 `finrl/meta/env_portfolio_allocation/env_portfolio.py`의 `StockPortfolioEnv`입니다. 환경 설정과 252일 공분산 입력은 [공식 PortfolioAllocation 예제](https://github.com/AI4Finance-Foundation/FinRL-Tutorials/blob/master/1-Introduction/FinRL_PortfolioAllocation_NeurIPS_2020.py)를 따릅니다. 이 원본 환경은 포트폴리오 비중으로 가치 변화를 계산합니다. `transaction_cost_pct`를 저장하지만 원본 `step()`에서 수수료를 차감하지 않으며, `reward_scaling` 적용도 주석 처리되어 있습니다. 실제 수수료 체결 환경으로 간주하지 않습니다. 기존 NumPy 환경에서 저장한 정책은 이어 학습하지 않습니다. GGUF 추론 설정과 프로젝트 전용 Expert 연결값은 [SETTINGS.md](SETTINGS.md)를 참조하십시오.


## 동결 Expert

`Desktop/모델/expert-packages`의 원본·양자화 패키지를 등록·선택합니다. 학습 가중치는 동결합니다. 새 정책은 Gymnasium의 `ObservationWrapper` API로 Expert 관측을 받습니다.

시장 예측과 매매 판단을 각각 평균·표준편차·최대 절댓값·실행 성공 수로 요약한 8개 관측값을 추가합니다. 직접 구현한 학습 Router·Fusion·Controller는 없습니다. 성공 수가 0이면 해당 그룹의 입력이 없는 상태이며, 실패 사유를 화면에 표시합니다. Expert 목록은 변경 시 다시 읽으며 선택에서 빠진 모델은 해제합니다. 새 종목 구성은 공식 환경의 행동 차원이 달라져 새 정책으로 시작해야 합니다.

패키지는 구조·가중치·입력 계약이 필요합니다. `.pt/.pth` 패키지와 가중치를 참조하는 GGUF JSON 패키지를 사용할 수 있습니다. 임의 확장자의 모델을 구조 정보 없이 자동 실행한다고 표시하지 않습니다. 양자화 부품의 GPU 상주와 부족분 RAM 오프로드는 Expert 로딩 계층에서 처리합니다.

## 실행

1. Git 서브모듈을 포함해 내려받습니다: `git clone --recurse-submodules <저장소 주소>`.
2. `설치.cmd`는 빠진 패키지를 설치합니다. 이미 설치된 배포판은 재설치·업그레이드하지 않습니다.
3. `서버켜기.cmd`를 실행하고 <http://127.0.0.1:8766>을 엽니다. FastAPI가 현재 SAC API와 React 빌드를 함께 제공합니다. 실행 스크립트는 설치된 도구로 타입 검사·빌드를 수행하고, 이 프로젝트의 서버 소유권을 확인해 기존 통합 서버를 재사용합니다. 패키지를 설치하거나 업그레이드하지 않습니다.
4. 통화·종목과 Expert를 선택해 공식 SAC 학습을 시작합니다.

```powershell
$env:PYTHONPATH="src"
$env:PYTHONUTF8="1"
.\.venv\Scripts\python.exe -m stockrl train --currency USD --symbols AAPL MSFT
.\.venv\Scripts\python.exe -m stockrl train --currency USD --symbols AAPL MSFT --resume
.\.venv\Scripts\python.exe -m stockrl backtest --currency USD --symbols AAPL MSFT
```

종목 개수 제한은 없습니다. 종목 수에 따라 공식 Replay의 RAM 사용량과 환경 차원이 증가합니다. USD와 KRW 데이터를 같은 학습 환경에 섞지 않습니다. 이것은 과거 가격을 사용하는 학습 환경이며 실제 증권 계좌가 아닙니다.

## 경로와 현재 지원 범위

- `FinRL-X/`: 변경하지 않은 공식 소스.
- `configs/experts.json`: Expert 등록·선택.
- `configs/instruments.json`: 시장·통화별 종목 목록.
- `data/finrl_trading.db`: 원본 가격 데이터 캐시.
- `runtime/official`: 새 SAC·Replay·체크포인트·실행 결과.
- `runtime/experts`: Expert 실제 추론 결과·실행기.
- `src/stockrl`: 공식 함수 호출과 Expert 연결부.
- `frontend/src/pages`: 학습·백테스트·Expert·데이터·모듈 조회 페이지.
- `frontend/src/components`: 공통 버튼·표·로그·차트·자원 표시 컴포넌트.

5173은 `frontend`에서 `npm run dev`로 실행하는 개발 서버 전용입니다. 개발 화면의 `/api`도 8766 통합 서버로 전달됩니다. 기존 루트 Streamlit 화면은 직접 실행이 비활성화되어 있으며 원문은 보존합니다. 공식 FinRL-X의 독립 예제 화면은 원본 상태로 유지합니다.

GitHub에는 모델 가중치·가격 캐시·가상환경·실행 상태를 올리지 않습니다. 다른 PC에는 필요한 Expert와 가격 데이터를 별도로 준비합니다.

백테스트는 원본 `BacktestEngine`의 투자 비중 100% 정규화·수수료·성과 계산을 그대로 사용합니다. 따라서 환경이 보유한 현금 비중을 그대로 재현하는 평가가 아닙니다. 기간 분리는 FinRL-X 원본 prepare_rolling_train / prepare_rolling_test를 호출합니다. 원본 예제처럼 전체 1,095일 구간에서 최근 365일을 평가용으로 분리합니다.

현재 제공하는 실행 경로는 실제 저장 가격의 학습·가상 체결·백테스트입니다. 키움 실시간 수신과 실제 주문은 이 새 경로에 연결하지 않았습니다. 공식 FinRL-X 실행부는 Alpaca용이며 키움과 동일한 기능으로 표시하지 않습니다. 공식 대시보드의 고정 예제 금액·임의 차트도 실제 상태처럼 표시하지 않습니다.
