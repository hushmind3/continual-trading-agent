# TradingMoE 운영 architecture

## integration-v1 architecture 결정

목표는 frozen 금융 Expert를 재사용하고 실제 체결 이후 확정된 NAV 결과로 상위 의사결정체를 지속 학습하는 것입니다. 일반 시뮬레이터의 episode reset으로 운영 계좌를 초기화하지 않습니다.

- **시장/실행:** 실시간 완료 시세 collector와 native Expert 입력, 독립 통화 계좌 및 지연 손익 계산을 사용합니다. FinRL-X 실행기를 베이스로 사용하지 않습니다. 가격 조회 실패 시 100을 반환하는 실행 경로와 현재 시장/브로커 규격이 맞지 않습니다.
- **학습:** TorchRL 0.14.0의 ClipPPOLoss와 TensorDict API를 사용합니다. 행동 당시의 joint probability와 policy version을 저장하고, 비중의 실제 sampling 분포와 학습 분포를 일치시킵니다. 과거 확률 없는 경험은 확률을 조작하지 않고 value 학습에만 사용합니다.
- **실행 분리:** Expert 본체를 복제하지 않는 작은 CPU learner와 한 batch로 제한된 작업 큐를 사용합니다. live collector는 학습 완료를 기다리지 않고, 완료된 trainable state만 판단 사이에 적용합니다. 계좌/DB writer는 collector 한 곳입니다. 새 미성숙 결과에는 현재 실제 시세 한 bar와 계좌 상태만 저장하고, native history는 Expert 입력에만 사용합니다.
- **복원:** optimizer, 정책 version, Python/NumPy/Torch RNG와 적용 경험 ID를 atomic small checkpoint에 포함합니다. checkpoint 성공 이전 경험은 소비하지 않습니다. 계좌와 미성숙 결과를 한 SQLite transaction으로 저장하며 JSON은 표시용 mirror입니다. 손상/유실된 JSON은 해당 상태에서 복구합니다. 제한된 자동 재시작과 backoff를 적용하고, 사용자의 정지 요청은 유지합니다.
- **평가:** 안정 정책과 학습 정책을 분리하고, Champion은 기본적으로 고정하고 Candidate/TradingMoE는 학습합니다. 고정한 두 상태의 capture 및 학습 cutoff 이후 실제 관측만 비교합니다. 평가 collector가 Feed에서 해당 구간을 수집하고 관측 진행량을 표시합니다. 수익·최대 손실폭·체결 비용 조건과 rollback을 유지합니다. 미학습 future holdout이 없으면 승격하지 않습니다.
- **Expert 결합:** native 입력과 두 계층의 learned gating/attention, Action Prior를 사용합니다. 사전 선별기는 결과 품질/실행 비용 개선 근거가 없어 추가하지 않습니다. 새 Expert는 명시된 입출력 규격/유효성 mask로 연결합니다.
- **종목 수:** 운영 universe는 Feed에 따라 가변이며 Controller를 재구축하지 않고 확장/축소됩니다. 특정 stock Expert의 원래 입력 universe는 그 Expert adapter의 규격입니다. 운영 universe의 상한으로 사용하지 않습니다.
- **자원:** available RAM, RSS/peak RSS, CPU, allocated/reserved/peak VRAM, load/transfer/inference/training/checkpoint 시간, queue wait, I/O를 측정합니다. 학습 큐가 꽉 차면 DB의 미학습 경험을 그대로 남기고 새 학습 enqueue를 중지합니다.

TorchRL은 전체 앱의 베이스가 아닌 학습 엔진입니다. Agent Lightning v1은 token/LLM 학습, 휘발성 store, native Windows local runner 제약 때문에 도입하지 않습니다. Tianshou 2.0.1은 custom policy 지원이 있지만 별도 buffer/collector 및 더 많은 의존성이 필요합니다. CleanRL은 이 환경 Python 3.13과 패키지 Python 제약이 맞지 않습니다. 대형 프로젝트 소스는 복사하지 않습니다. exchange-calendars 4.13.2의 API로 주식 휴장일을 판단합니다. crypto/FX/futures에는 주식 calendar를 적용하지 않습니다.

## 재현 가능한 기준 측정

기준 HEAD: `72d213b488ebe825360816ec3f3e0be61f030c57`.
Python 3.13.3 / Torch 2.14.0+cu132 / RTX 3070 / RAM 31.92 GiB.
전체 Python 테스트: 148/148, 20.149초.
동일 비교 fixture: 1종목, Expert 계약 2개, CPU intra-op thread 4, warmup 5회 후 판단 35회, 학습 경험 32개, replay 128행. fixture는 운영 계좌/데이터에 쓰지 않습니다.

| 항목 | 기준 |
|---|---:|
| 판단 p50 / p95 | 1.372 / 1.432 ms |
| 학습 경험/초 | 97.99 |
| 학습 CPU 시간 / wall | 1.234 / 0.327 s |
| RSS / peak RSS | 760.24 / 760.24 MiB |
| fixture model 구성 | 1.94 ms |
| small checkpoint 시간 / 크기 | 5.06 ms / 468.42 KiB |
| replay 기록 / 읽기 | 200.69 / 47288.31 행/초 |

이 수치는 실제 native Expert 전체 inference latency나 수익률 검증이 아닙니다. 학습·계좌 연결과 cold import를 포함한 resource 비용 비교용 기준입니다.

## 경로와 설정

원본/운영 모델: 바탕화면 `모델`. vendor source/native datasets: `artifacts/experts`. 계좌·미성숙 결과·경험·evidence: 각 운영 상태 디렉터리. frozen 본체 `.pt`와 작은 `.trainable.pt`를 함께 복원합니다. 설정의 authoritative 경로는 `configs/online_learning.json`입니다.

실시간 모드는 `scripts/run_native_vertical_trading.py --mode live --market <collector CSV>`입니다. 과거 입력은 명시적인 `--mode historical`에서만 사용합니다. 실제 주문은 별도 broker 실행 adapter가 필요하며 paper 실행을 실제 주문으로 주장하지 않습니다.

## 공개 구현 선택 근거

| 공개 구현 | 확인한 최신 상태 | 채택 판단 |
|---|---|---|
| [TorchRL](https://github.com/pytorch/rl/tree/4ad8b0fccdeeb85866db3e3b6d5fb3aefebd31f0) | main 2026-10-06, release 0.14.0 | ClipPPOLoss / TensorDict / GlobalRNGState API 채택. 동일 machine에서 실제 numerical/복원/동시성 테스트 실행. generic trading env의 random price/holding shaping reward는 사용하지 않음. |
| [FinRL-X](https://github.com/AI4Finance-Foundation/FinRL-Trading/tree/4409abe925c904e570be78ebfb5e77ac3491dff8) | 2026-09-18 소스 | RLModel은 기존 FinRL/SB3 wrapper이며 Alpaca executor 가격 오류 fallback 100이 있어 운영 베이스로 선택하지 않음. walk-forward/target-weight 실행 분리는 검토함. |
| [Agent Lightning](https://github.com/microsoft/agent-lightning/tree/d381995396274039f2bb1cbe5ff42ac8067f4e47) | 2026-09-29, 1.0.2 | store가 in-memory이고 local runner는 native Windows를 거부함. verl/vLLM token 학습이 이 정책 공간과 맞지 않아 미채택. |
| [Tianshou](https://github.com/thu-ml/tianshou/tree/f2402056b03acafeedf2518a5088db55add004ab) | 2026-04-03, 2.0.1 | async collector의 vector-env 즉시 reward/buffer 경로를 별도로 다시 연결해야 하며 dependency가 더 큼. TorchRL 대신 사용할 명백한 이득을 찾지 못해 미채택. |
| [CleanRL](https://github.com/vwxyzjn/cleanrl/tree/fe8d8a03c41a7ef5b523e2e354bd01c363e786bb) | 2026-04-20 소스 | source package는 Python <3.11, Torch 2.4.1 등 제약을 선언하며 single-file 중심. 현재 Python 3.13 운영 베이스에 부적합. |
| [exchange-calendars](https://github.com/gerrymanoim/exchange_calendars/releases/tag/4.13.2) | 2026-03-10, 4.13.2 | 2026 KRX 등을 포함한 실제 session API 사용. 휴장일 skip과 정상 거래일 테스트 통과. |

TorchRL Trainer의 현 release 구현은 prototype으로 표시되어 있고 일반 Collector의 즉시 환경 step은 실제 지연 손익과 바로 맞지 않습니다. 전체 앱을 외부 framework 하나로 대체하지 않고, 검증된 정책/저장 API와 native 시장·체결 boundary를 결합합니다. 시뮬레이터를 live Environment로 주장하지 않습니다.

## 동일 조건 재측정

`python scripts/benchmark_online.py --revision 72d213b` 및 revision 없는 실행을 비교합니다. 측정은 stdout으로 출력하고 운영 파일은 쓰지 않습니다.

| CPU fixture: 32개 경험, 4 threads | 기준 | target |
|---|---:|---:|
| 판단 p50 / p95 | 1.369 / 1.689 ms | 1.624 / 2.010 ms |
| 학습 경험/초 | 110.43 | 319.73 |
| optimizer step 수 | 32 (개별 update) | 1 (32개 batch) |
| 학습 wall / CPU 시간 | 0.290 / 1.141 s | 0.100 / 0.422 s |
| RSS / peak RSS | 786.33 MiB | 786.53 MiB |
| small checkpoint 시간 / 크기 | 4.60 ms / 468.89 KiB | 8.47 ms / 483.35 KiB |
| replay 기록 / 읽기 | 204 / 60486 행/초 | 192 / 54563 행/초 |

두 비교 process에 동일한 현재 benchmark harness가 import되므로 이 표의 RSS는 새 라이브러리 cold-import 차이를 분리한 수치가 아닙니다. 기존 별도 초기 기준 760.24 MiB와 직접 같은 측정으로 취급하지 않습니다. replay 차이는 작은 표본의 변동이며 개선으로 주장하지 않습니다. batch 처리량 증가를 optimizer step당 동일 학습 효과나 수익 증가로 주장하지 않습니다.

`--compare-inputs`는 실제 Feed 250종목의 동일한 frame/일봉을 메모리에 고정합니다. 기준 20.788초 → target 3.724초. 동일 17개 특징과 forward-fill/mask를 유지하면서 중복 준비와 pandas iterrows 배열 입력을 제거했습니다.

`--native`는 실제 원본 모델 20개를 load하고 실제 저장 native 입력으로 GPU에서 실행합니다. 전체 model load 25.93 → 19.26초, peak RAM 4634.67 → 4635.96 MiB. TimesFM warm 31.69 → 29.54 ms, MacroHFT warm 6.62 → 5.84 ms; peak VRAM 각각 83.90 / 8.31 MiB로 동일합니다. load/warm 시간에는 OS file/page cache 효과가 있으므로 architecture만의 속도 향상으로 주장하지 않습니다. 원본 Expert 가중치는 수정하지 않습니다.

`--stress-seconds 120`에서 synthetic concurrent 학습/판단 4115 update, 131680 경험을 처리했습니다. 판단 p50 2.60 ms / p95 7.23 ms, 오류 0, 종료 후 queue 0. 초기 optimizer/kernel warmup을 포함한 RSS 증가 102.36 MiB, peak 790.47 MiB. 이 테스트는 운영 계좌/시세를 쓰지 않습니다. 수시간·수일 운영 안정성이나 수익 향상을 검증한 결과는 아닙니다.

`--live`에서 실제 Feed 259종목 → 시장 Expert 7개 + stock Policy 5개 → 최종 행동/비중의 경로를 실행했습니다. 준비 5.26초, native/controller 판단 및 page trim 10.48초. peak RSS 10692.28 MiB; 모든 frozen mmap 페이지가 계속 resident일 때의 수치입니다. Native 실행 이후 Windows working-set trim으로 resident 페이지를 OS에 반환했으며 마지막 RSS는 27.07 MiB, available RAM은 16.11 GiB였습니다. 이 마지막 RSS를 모델의 실제 크기나 총 사용 RAM으로 해석하면 안 됩니다. 재접근 시 페이지가 다시 resident가 되고, peak 자체는 줄어들지 않습니다. 판단 중 최대 native VRAM 증가량은 FinCast 약 3.70 GiB였고, 끝난 뒤 Torch GPU allocated는 약 11.9 MiB였습니다.

이 과정에서 Toto의 37개 관측 입력이 patch size 32를 만족하지 못하는 실제 오류를 발견했습니다. 원본 forecast API의 target_mask로 왼쪽 padding을 미관측 처리하여 모든 실제 관측을 보존합니다. native Expert가 CUDA RNG를 재설정하던 경로도 CPU/CUDA fork_rng로 격리하여 상위 정책의 sampling RNG를 보존합니다. 원본 모델 source/가중치는 바꾸지 않습니다.

## 현재 실행상의 조건

- 실제 주문 실행은 아직 별도 broker 실행 adapter가 필요합니다. 가상 체결은 사용 가능합니다.
- MacroHFT native 36+9, MarketGPT native ITCH의 contemporaneous stream이 없으면 해당 Expert는 입력 부족으로 표시됩니다. 과거 데이터로 조용히 대체하지 않습니다.
- 원래 stock policy의 전체 학습 universe가 확보되지 않으면 그 정책은 차단됩니다. 시장 데이터가 있다는 이유로 입력 규격을 조작하지 않습니다.
- 승격에는 설정된 최소 미래 관측량(기본 390분)이 필요합니다. 데이터가 쌓이기 전 승격 완료를 주장하지 않습니다.

## 변경 위치

| 관심 영역 | 소스 |
|---|---|
| 행동/비중 분포 및 behavior metadata | `moe_policy.py` |
| TorchRL batch objective | `moe_training.py` |
| bounded CPU learner / staged publication | `moe_learner.py` |
| future holdout 수집/검증 | `moe_evaluation.py` |
| native Expert / 구성 / small state | `trading_moe.py`, `moe_native.py` |
| 실제 시장 입력 | `moe_live.py`, `live_feed.py`, `market_panel.py` |
| 계좌·손익·경험 복구 | `moe_paper.py`, `rewards.py`, `replay_store.py`, `state_io.py` |
| 자원 측정과 native admission | `gpu_scheduler.py` |
| 실행 / 복원 / API | `scripts/run_native_vertical_trading.py`, `web/trading_moe.py`, `web/runtime.py` |

검증: 최종 Python 테스트 175/175 통과(23.874초). 원본 stock Policy 6개의 frozen 실행, dynamic 종목 수 1→17→5, live 입력/가상 체결/지연 손익, behavior 저장·재시작 후 실제 정책 update, optimizer/RNG 복원, 실패 rollback, 미래 평가 구간, canonical 계좌 복원, CPU/RAM/GPU admission, native CUDA RNG 격리, Toto patch mask를 포함합니다. GPU benchmark와 GPU 소유권 테스트는 동시에 실행하지 않습니다.
