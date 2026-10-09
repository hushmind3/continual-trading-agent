# FinRL-X MoE 운영

실시간 시세와 고정 Expert를 이용해 중앙 정책 하나가 목표 비중을 결정하고, 공식 SAC 엔진으로 경험을 반복 학습하는 운영 도구입니다.

## 사용하는 공식 모듈

| 기능 | 실제 호출 |
| --- | --- |
| 데이터 정제 | FinRL-X `DataProcessor._clean_price_data` |
| 가격 저장·조회 | FinRL-X `DataStore.save_price_data / get_price_data` |
| 전략 규격 | FinRL-X `BaseStrategy / StrategyResult` |
| 백테스트·성과 지표 | FinRL-X `BacktestEngine.run_backtest / BacktestResult` |
| 목표 비중 → 주문 | FinRL-X `TradeExecutor.execute_strategy` |
| 모의 체결·현금·보유 수량 | FinRL `StockTradingEnv.step` |
| 보상 수익 계산 | FinRL-X `performance_analyzer.calculate_returns` |
| 모델 저장·복원 | SB3 `SAC.save / SAC.load` |
| 실행 점검 예약 | APScheduler `BackgroundScheduler` |
| 중앙 학습 | Stable-Baselines3 `SAC.train` |
| Actor·Twin Critic·Target Critic | Stable-Baselines3 `SACPolicy` 기본 클래스 |
| 경험 재사용 | Stable-Baselines3 `DictReplayBuffer` |
| Replay 재시작 복원 | Stable-Baselines3 `save_replay_buffer / load_replay_buffer` |

FinRL-X의 SAC 예제도 FinRL의 DRLAgent를 통해 Stable-Baselines3를 사용합니다. 이 프로젝트는 실시간 입력과 MoE 등록을 위해 그 공식 SAC 엔진을 직접 호출합니다. 예제의 `train_sac()` 함수를 호출한다고 표시하거나 학습 알고리즘을 복사하지 않습니다.

## 실행 흐름

`키움·공개 시세 → FinRL-X 정제·저장 → 동결 Expert → MoE → 공식 SAC Actor → 목표 비중·현금 → 가상체결 → 비용 반영 계좌 보상 → 공식 Replay → SAC 학습`

중앙 MoE는 512차원, Attention 8 heads / KV 4 heads, SwiGLU 1,792차원, RMSNorm입니다. Qwen 공개 Attention·SwiGLU·RMSNorm 구현을 사용합니다. 이 금융 입력 구성은 Qwen 원본 언어 모델 전체나 FinRL-X 기본 신경망 설정이 아닙니다.

MoE는 공식 정책의 `BaseFeaturesExtractor`로 등록합니다. 종목별로 동일한 Actor·Critic을 공유하고 종목 비중 점수와 현금 선호를 함께 출력합니다. 종목 수는 고정하지 않습니다. 계좌의 실제 보상은 해당 통화의 종목 경험에 공유합니다. 종목별 독립 수익을 추정해 저장하는 방식은 아닙니다.

기존 Gaussian 행동 기록은 동일한 목표 비중을 만드는 SAC 행동으로 재표현해 재사용합니다. 입력 차원을 확인할 수 없는 기록은 버퍼에서 제외합니다. 원래 계좌 보상·체결 비용을 변경하지 않습니다.

백테스트는 공식 엔진을 사용하며 전략 구성 훅에서 기록 비중과 다음 관측 체결을 지정합니다. 원본의 투자 비중 100% 정규화를 우회해 모델이 선택한 현금 비중을 유지합니다. 키움과 통화별 원장·화면 표시 형식은 연결 어댑터입니다. 공식 TradeExecutor에는 가상계좌 어댑터를 전달하고, 실제 체결 계산은 공식 StockTradingEnv로 실행합니다. Alpaca 네트워크 주문은 호출하지 않습니다.

## GPU와 저장

- 동결 Expert는 양자화 버전을 우선하고 GPU에 상주합니다. VRAM 초과분만 RAM 또는 레이어 오프로드합니다.
- SAC Actor와 Q 네트워크, Adam 상태는 GPU의 FP32입니다. 운영 추론은 CUDA BF16 autocast를 사용합니다.
- 시세 수집과 API는 별도 프로세스입니다. Expert·판단·학습은 통합 GPU 프로세스의 별도 작업이며 판단은 마지막 발행 가중치를 사용합니다.
- `champion.pt`는 선택된 동결 Expert 몸체와 중앙 학습 상태를 포함합니다. 정상 정지·구성 변경 때 최신 중앙 상태를 봉합합니다.
- Replay는 최대 개수와 RAM 예산 중 작은 값으로 제한합니다. 샘플은 RAM에 두고 선택 배치만 GPU로 옮깁니다.
- 공식 SAC.save / SAC.load로 Actor·Critic·Target Q·각 optimizer·엔트로피 상태를 저장합니다. 부품 교체 시 남은 슬롯과 optimizer 상태를 이어받습니다.
- KRW·USD 계좌와 비용·체결 기록은 분리합니다.
- FinRL-X에 없는 Windows 프로세스 예약은 APScheduler에 맡기며, 현재 작업 상태·재시도 조건만 연결부에서 처리합니다.
- 일봉과 분봉 모두 공식 FinRL-X DataStore로 저장합니다. `configs/market_context.json`은 동결 Expert 입력용 기간 설정입니다.

## 실행

Python 3.13, Node.js LTS, NVIDIA 드라이버를 준비하고 `설치.cmd`를 실행합니다. `서버켜기.cmd`는 API와 Vite를 함께 켭니다.

- 운영 UI / API: <http://127.0.0.1:8766>
- 개발 UI: <http://127.0.0.1:5173>
- 모델: `Desktop/모델/champion.pt`
- 설정: `configs/operations.json`
- 계좌·경험·시세: `runtime/finrlx`
- 정책·Replay: `runtime/finrlx/policies`
- Expert 부품 라이브러리: `Desktop/모델/expert-packages`

모델·runtime·인증 정보·가상환경·node_modules는 GitHub에서 제외합니다. 다른 PC에서 모델과 학습·계좌를 이어가려면 모델 폴더와 runtime을 함께 옮깁니다.

## 확인

```powershell
$env:PYTHONPATH="src"
$env:PYTHONUTF8="1"
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
cd frontend
npm run typecheck
npm test
npm run build
```

[구조](docs/architecture.md) · [설치](docs/windows-install.md) · [저장 위치](docs/project-storage.md)
