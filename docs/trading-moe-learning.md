# TradingMoE 운영 architecture

## integration-v1 architecture 결정

목표는 frozen 금융 Expert를 재사용하고 실제 체결 이후 확정된 NAV 결과로 상위 의사결정체를 지속 학습하는 것입니다. 일반 시뮬레이터의 episode reset으로 운영 계좌를 초기화하지 않습니다.

- **시장/실행:** 실시간 완료 시세 collector와 native Expert 입력, 독립 통화 계좌 및 지연 손익 계산을 사용합니다. FinRL-X 실행기를 베이스로 사용하지 않습니다. 가격 조회 실패 시 100을 반환하는 실행 경로와 현재 시장/브로커 규격이 맞지 않습니다.
- **학습:** TorchRL 0.14.0의 ClipPPOLoss와 TensorDict API를 사용합니다. 행동 당시의 joint probability와 policy version을 저장하고, 비중의 실제 sampling 분포와 학습 분포를 일치시킵니다. 과거 확률 없는 경험은 확률을 조작하지 않고 value 학습에만 사용합니다.
- **실행 분리:** Expert 본체를 복제하지 않는 작은 CPU learner와 bounded 작업 큐를 사용합니다. live collector는 학습 완료를 기다리지 않고, 완료된 trainable state만 판단 사이에 적용합니다. 계좌/DB writer는 collector 한 곳입니다.
- **복원:** optimizer, 정책 version, Python/NumPy/Torch RNG와 적용 경험 ID를 atomic small checkpoint에 포함합니다. checkpoint 성공 이전 경험은 소비하지 않습니다.
- **평가:** 안정 정책과 학습 정책을 분리하고, 고정한 두 상태의 학습 cutoff 이후 실제 관측만 비교합니다. 수익·최대 손실폭·체결 비용 조건과 rollback을 유지합니다. 미학습 future holdout이 없으면 승격하지 않습니다.
- **Expert 결합:** native 입력과 두 계층의 learned gating/attention, Action Prior를 사용합니다. 사전 선별기는 결과 품질/실행 비용 개선 근거가 없어 추가하지 않습니다. 새 Expert는 명시된 입출력 규격/유효성 mask로 연결합니다.
- **자원:** available RAM, RSS/peak RSS, CPU, allocated/reserved/peak VRAM, load/transfer/inference/training/checkpoint 시간, queue wait, I/O를 측정합니다. 학습 큐가 꽉 차면 DB의 미학습 경험을 그대로 남기고 새 학습 enqueue를 중지합니다.

TorchRL은 전체 앱의 베이스가 아닌 학습 엔진입니다. Agent Lightning v1은 token/LLM 학습, 휘발성 store, native Windows local runner 제약 때문에 도입하지 않습니다. Tianshou 2.0.1은 custom policy 지원이 있지만 별도 buffer/collector 및 더 많은 의존성이 필요합니다. CleanRL은 이 환경 Python 3.13과 패키지 Python 제약이 맞지 않습니다. 대형 프로젝트 소스는 복사하지 않습니다.

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
