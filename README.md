# FinRL-X · FinRL · SB3 SAC + React

현재 구현의 구조 설명은 이 README에 통합합니다. React는 `f1539571604f23a05f47761b25fc0448d1a12db5`의 흰색 테마·7개 메뉴·공통 컴포넌트를 유지합니다. 과거 커밋으로 백엔드를 되돌리지 않았습니다. 가상계좌·시세·모델 도구의 기존 소스만 복구하고 현재 API에 연결했습니다. PPO 학습기·중앙 Router/Fusion/Controller는 실행하지 않습니다. Frozen Expert에 포함된 PPO 정책의 추론은 SAC 학습기와 별개입니다.

## 폴더와 진입점

```text
frontend/
  src/App.tsx                 메뉴 해시 라우팅
  src/shell/                  기존 화면 레이아웃
  src/pages/                  운영·MoE·시장·계좌·학습·연결·진단 화면
  src/pages/model/            Expert 등록·선택·적재·추론·변환·외부 폴더
  src/pages/portfolio/        가상계좌·백테스트 결과 표
  src/pages/training/         SAC 제어·Actor/Critic·체크포인트
  src/data/                   HTTP 요청·폴링·타입·Expert 분류
  src/ui/                     공통 Button·Panel·Drawer·표·상태·로그
  package.json / package-lock.json / vite.config.ts / tsconfig.json
  dist/                       운영 빌드 산출물, Git 제외
  node_modules/               설치 의존성, Git 제외
src/stockrl/
  web_api.py                  FastAPI + React 정적 제공
  __main__.py / official_cli.py CLI → 현재 프레임워크 함수
  framework.py                FinRL-X·FinRL·SB3 호출, 선택한 정책 경로
  job_worker.py               별도 SAC/백테스트/수집 작업과 저장 기록
  expert_registry_native.py   현재 Registry, 동결 추론, 8개 관측 요약
  expert_observation.py       원본 환경을 감싼 Gymnasium ObservationWrapper
  moe_native.py               패키지 원본 구조와 runner로 추론
  moe_stock_policies.py       기존 주식 Expert의 원본 입력·정책 추론
  expert_device.py            기존 Expert 장치 이동
  paper_account.py           기존 KRW/USD 가상 원장·체결·손익
  live_feed.py                기존 Yahoo/Kraken 수집과 완료 바 전달
  kiwoom_stream.py            기존 키움 이벤트·OHLCV 파서
  provider_credentials.py    기존 OS 보안 저장소·키움 인증
  market_storage.py          완료 바를 공식 DataStore에 추가
  multiscale.py              기존 DailyBarStore (시세 일봉 보관)
  platform/
    operations_runtime.py    위 기능의 운영 연결부, SAC 추론 → 기존 원장
    operations_settings.py   학습값과 분리된 기존 운영 필드
    library_operations.py    기존 모델 도구의 비동기 API 연결부
    assets.py / expert_residency.py      기존 ExpertPool·RAM/VRAM 적재
    expert_packages.py / expert_contracts.py 패키지 검증·입력 계약
    observations.py                     현재 원본 입력 생성
    library_store.py / native_upgrade.py 패키지 조회·등록·동일 구조 가중치 연결
    expert_discovery.py / github_discovery.py / expert_search_metadata.py
    expert_acquisition.py               기존 검색·다운로드·패키지 자동 등록
    expert_conversion.py / expert_comparison.py / expert_optimizer.py
    quantized_linear.py / nf4_linear.py / work_devices.py
    gguf_registration.py / gguf_format.py / gguf_expert.py / llama_engine.py
    hf_forecast.py / kiwoom_data.py / sessions.py / resources.py
configs/experts.json            Expert 이름·역할·파일 참조·입력 계약·활성 목록
configs/instruments.json        현재 종목·시장·통화·시세 공급원 목록
configs/local/                 인증 공급원·운영 설정 (Git 제외)
requirements/operations.txt     Python 의존성
scripts/start_server.py         통합 서버 실행·소유권 확인
scripts/install_windows.py      기존 누락 의존성 설치 스크립트
서버켜기.cmd                   8766 운영 진입점
FinRL-X/                       공식 FinRL-Trading Git 서브모듈, 수정하지 않음
data/                          실제 가격 DB, Git 제외
runtime/official/              SAC·Replay·작업·체크포인트·백테스트, Git 제외
runtime/experts/               동결 추론 결과·외부 실행기, Git 제외
runtime/operations/            가상원장·시세 수신·모델 도구 작업 상태, Git 제외
results/ / .venv/              공식 실행 산출물 / 설치 환경, Git 제외
휴지통/                        폐기 전용, 코드와 연결하지 않음, Git 제외
```

`expert_backends.py`, `expert_registry.py`, `paths.py`는 원본 Frozen Expert runner가 사용하는 정의·시간·JSON·경로 계약을 보존합니다. `state_io.py`는 현재 상태 파일의 원자적 기록을 담당합니다. 서로 다른 역할의 `src/dist`, `.venv/node_modules/runtime`는 중복 소스로 취급하지 않습니다.

## React → FastAPI → 실제 모듈

`main.tsx` → `OperationsProvider` → `App.tsx` → 화면 컴포넌트 순서입니다. `data/api.ts`의 `request()`가 `/api`를 호출하고 `OperationsProvider`가 `/api/state`를 주기적으로 읽습니다. 공통 상태에는 저장 정책·가격·동결 추론·자원·가상계좌·모델 작업 상태가 포함됩니다. 상태 조회는 학습·거래·다운로드를 시작하지 않습니다.

운영 8766은 `web_api.react_index()`와 `/assets`에서 `frontend/dist`를 제공합니다. 개발 5173은 Vite이며 `vite.config.ts`가 `/api`를 8766에 전달합니다.

| 메뉴 | 실제 HTTP 엔드포인트 (`/api` 접두사) | 호출 함수·소스 |
| --- | --- | --- |
| 운영 `#control` | GET state, POST controls/{feed,paper,engine} | `web_api.state`, `OperationsRuntime.command` |
| MoE `#moe` | GET state/models/library, POST experts/register, experts/select, library/{kind} | `ExpertRegistry.register/select`, `model_files`, `LibraryOperations.start/_execute` |
| 시장 `#markets` | GET state/prices/connections, POST collect, controls/feed | `price_history`, `job_worker.main` → FinRL-X `fetch_price_data`; `LiveMarketCollector.run` |
| 계좌 `#portfolio` | GET state/result/{weights,trades}, POST orders, preflight/backtest, backtest | `OperationsRuntime.manual_order` → `PaperAccount._fill`; `framework.backtest` → `BacktestEngine.run_backtest` |
| 학습 `#learning` | GET state/checkpoint, POST preflight/train, train, stop, checkpoints/restore | `preflight`, `launch`, `stop`, `restore_checkpoint` → 현재 SB3 SAC |
| 연결 `#connection` | GET connections/provider/settings, POST provider/{connect,test,public}, settings | 기존 `connect_credentials/test_connection`, `operations_settings.update` |
| 진단 `#system` | GET state/logs/modules | `ResourceMonitor.snapshot`, 실제 저장 로그·소스 함수 목록 |

다운로드는 GET `/api/download/{name}`으로 기존 백테스트 결과·현재 SAC 파일을 제공합니다. 체크포인트 다운로드는 GET `/api/checkpoint?path=...`입니다. 등록·선택·교체·해제는 같은 `configs/experts.json`의 슬롯/활성 목록을 사용합니다. 별도 Registry를 만들지 않습니다.

`library/{kind}` 작업: `inspect`, `import`, `probe`, `load`, `unload`, `search`, `acquire`, `convert`, `optimize`, `apply`. 작업 결과·진행·오류는 `runtime/operations/library-job.json`에 기록되어 React에서 표시됩니다. API 요청 수락과 실제 작업 성공은 구분합니다.

## 공식 프레임워크 역할과 학습 연결

| 프레임워크 | 현재 담당 |
| --- | --- |
| FinRL-X (서브모듈 FinRL-Trading) | DataStore, DataProcessor, FMP 수집, rolling 구간, `train_sac(agent)`, StrategyResult, BacktestEngine |
| 설치된 FinRL | FeatureEngineer, StockPortfolioEnv, DRLAgent 학습·예측 호출 |
| 설치된 Stable-Baselines3 | SACPolicy/MlpPolicy, Actor/Twin Critic, Optimizer/Loss, Replay, 공식 save/load |

학습 경로:

1. React `SacControls` → `preflight/train` → `web_api.launch` → 별도 `stockrl.job_worker`.
2. `official_cli.main` → `framework.prices(currency,symbols)` → 공식 DataStore의 실제 가격.
3. `framework.training_environment` → FinRL `FeatureEngineer` → 원본 252일 공분산 입력 → FinRL-X rolling 구간 → 원본 `StockPortfolioEnv`.
4. `ExpertObservation.observation` → `ExpertRegistry.outputs` → ExpertPool → 원본 관측을 펼친 값 + 시장/매매별 평균·표준편차·최대 절댓값·성공 수 8개.
5. `framework.train` → FinRL-X 원본 `train_sac(agent)` → FinRL `DRLAgent` → SB3 SAC. 이어 학습은 원본 `SAC.load`와 `load_replay_buffer`를 사용합니다.
6. 완료 시 `sac.zip`, `replay.pkl`, `dataset.json`을 저장합니다. 작업 stdout 로그는 `runtime/official/jobs/`에 기록됩니다.

현재 예제 설정은 `batch_size=128`, `buffer_size=100000`, `learning_rate=0.0003`, `learning_starts=100`, `ent_coef="auto_0.1"`, 실행 50,000단계입니다. 나머지 SAC 설정은 설치된 라이브러리 기본값입니다. 기본 Actor/Critic은 `[256,256]`입니다. 화면은 `source_settings()`가 실제 예제 AST·설치 클래스에서 읽은 값을 표시합니다. 이번 연결 작업은 알고리즘·기본값·환경 규칙을 바꾸지 않았습니다.

환경 인자는 기존 `framework.training_environment` 그대로입니다. 원본 Portfolio 환경의 `step()`은 포트폴리오 가치 환경이며 실제 증권사 체결이 아닙니다. PaperAccount는 별도의 기존 가상 원장입니다. 두 계층의 손익과 수수료 계산을 동일하다고 설명하지 않습니다.

## Replay · 정책 버전 · 백테스트

`job_worker`는 학습 실행 전에 현재 SAC·Replay·dataset을 `runtime/official/archives/{job_id}`에 보관합니다. `restore_checkpoint()`는 환경·예제 식별정보와 SB3 로딩을 확인한 뒤 `active-checkpoint.json`에 선택 경로만 기록합니다. 가중치 파일을 덮어써 복원하지 않습니다. `framework.policy_files()`가 선택한 폴더에서 정책·Replay·식별정보를 읽고, 이후 학습 결과는 현재 경로에 저장합니다. 현재 종목·통화와 맞지 않는 이어 학습은 기존 식별 검사를 사용합니다.

백테스트: `official_cli.main` → `framework.backtest` → 원본 `training_environment(training=False)` → SB3 `SAC.load` → FinRL `DRLAgent.DRL_prediction` → FinRL-X `StrategyResult` → `BacktestEngine.run_backtest`. 결과 가치·지표·가중치·거래 기록을 `backtest.csv`, `backtest_metrics.json`, `backtest_weights.csv`, `backtest_trades.csv`로 기록하고 React가 조회합니다. 원본 BacktestEngine의 비중 정규화·비용 계산은 유지합니다.

현재 로컬 `sac.zip`은 이전 환경·다른 설정의 파일입니다. 현재 FinRL 원본 환경과 호환되는 정책을 학습하기 전에는 이어 학습·백테스트·자동 판단을 정상 실행된 것으로 표시하지 않습니다. 원본 파일과 Replay는 보존했습니다.

## 외부 모델과 Frozen Expert 계약

모델 기준 경로는 현재 사용자 `Desktop/모델`이며 저장소 안으로 강제 이전하지 않습니다. 실제 Expert 이름·역할·원본/양자화 구분·상대 파일명·SHA256·크기·종목·최소 이력·실행기는 [configs/experts.json](configs/experts.json)에 있으므로 여기서 동일 목록을 복제하지 않습니다.

- `expert-packages/*.pt`: `frozen_expert_package_v1`, `entry`, `state_dict`, `metadata`, `module_count`, `feature_size`. 구조 소스·원본 runner·입력 계약이 함께 있어야 합니다.
- GGUF JSON 패키지: 같은 패키지 형식, `executor=llama_cpp`, `weight_asset`가 실제 `.gguf` 상대 파일·크기·checksum을 참조합니다. 예: `expert-packages/qwen35_08b_gguf.json` → `expert-packages/444406ddd926550c724ec18d.gguf`.
- `champion.pt`: 확인한 형식은 `registered_vertical_trading_moe_v2`, 기존 12개 Expert 참조를 담습니다. 현재 SAC 중앙 정책으로 로드하지 않습니다. 필요한 Frozen Expert 참조만 선택 등록합니다.
- `experts/`의 개별 원본 가중치는 `native_upgrade.inspect_native/match_weights`가 기존 입력 템플릿과 실제 tensor 이름·크기를 대조합니다. 구조가 맞지 않는 파일은 구체적인 이유를 반환합니다.

등록 경로: `/api/models` 파일 조회 → `library/inspect` 원본 계약 조회 → `library/import` 참조 등록 → 현재 Registry → `ExpertPool.get/run`. 외부 폴더의 기존 패키지는 참조를 등록하고 원본을 복사·수정하지 않습니다. 새로운 다운로드와 변환 결과는 기존 `expert-packages`의 별도 파일로 저장하며 원본과 구분됩니다.

입력은 `observations.native_input`의 완료 가격 시계열/OHLCV 또는 `StockPolicyExpert.prepare_input`의 원본 종목·지표·USD 계좌입니다. Chronos/TimesFM의 기존 계약은 실제 SPY 일봉 초과수익률을 요구합니다. 출력 packet은 `native_output`, `symbols`, `as_of`, `layout`, `units`를 갖고 관측 요약에 전달됩니다. 입력 부족·형식 불일치·실패는 오류/실패 기록으로 표시하며 결과를 만들어 채우지 않습니다.

실행기는 기존 `NativeExpert`, `StockPolicyExpert`, `HfForecastExpert`, `GGUFExpert`입니다. Torch·Transformers·Chronos·TimesFM·bitsandbytes·Accelerate·safetensors 및 llama.cpp 외부 실행기가 필요합니다. `llama_engine.ensure_engine`의 기존 실행기 준비 경로는 `runtime/.../engines`입니다. GGUF 가중치를 다시 다운로드하는 기능과 실행기 준비는 서로 다릅니다.

UI 적재는 `ExpertPool`과 기존 `Residency.preload/release`를 사용합니다. 현재 API의 적재 여부와 현재 자원 측정은 `current_resources/loaded`, 마지막 다른 학습 프로세스의 측정·출력은 `runtime/experts/status.json` 기록으로 구분합니다. 파일 크기를 RAM/VRAM 실측으로 표시하지 않습니다. 실제 추론은 사용자가 `probe`를 요청할 때 기존 실행기로 수행합니다.

검색·획득은 기존 HF/GitHub 검색과 tensor 구조·revision 확인 함수를 사용합니다. 변환은 기존 FP16/BF16/INT8/INT4/NF4 변환 함수, 최적화는 기존 품질 비교·정밀도 선택 함수를 호출합니다. 동일 실제 입력의 cold/warm 추론 측정은 사용자 요청 작업 안에서만 실행됩니다. 변환 및 최적화 작업을 이 복구 세션에서 실행하지 않았습니다.

## 시장 데이터 · 가상계좌 · 키움 · 운영 설정

`OperationsRuntime.command('feed',True)` → 기존 `LiveMarketCollector.run/collect_once` → 완료 Yahoo/Kraken 바 또는 `BrokerStreams` 키움 입력 → `AppendOnlyMarketCSV.append` → FinRL-X DataProcessor/DataStore → `OperationsRuntime.accept` → 기존 `PaperAccount.process_bar/save`. 과거 캐시 압축 코드를 공식 가격 DB에 적용하지 않아 기존 가격 이력을 지우지 않습니다. 실시간 입력은 수신한 완료 바 기준이며 저장 가격을 실시간 수신이라고 표시하지 않습니다.

가상계좌는 기존 독립 KRW 1,000만 원/USD 1만 달러 원장을 사용합니다. `manual_order`는 수신 시세 또는 실제 저장 가격을 명시하여 기존 `_fill`을 호출합니다. 보유·잔고·체결·실현/평가 손익과 pending 주문은 기존 원장 계산을 사용합니다. 시세 수신과 가상체결 활성화는 별도 제어입니다. 증권사에 실제 주문을 전송하지 않습니다.

SAC 자동 판단은 `OperationsRuntime.sac_decision` → 현재 원본 환경/ExpertObservation → `SAC.load/predict` → 환경의 원본 `softmax_normalization` → 기존 `PaperAccount.queue_decisions`입니다. 가상 원장 규칙이나 새 학습기를 구현하지 않습니다. 호환 정책·실제 관측이 없는 경우 `policy_error`를 표시합니다.

키움: 기존 `provider_credentials.connect_credentials/test_connection` → OS keyring 보안 저장소; 공급원·환경·마지막 인증 상태만 `configs/local/provider_settings.json`에 기록합니다. 시세 수송은 기존 `platform/kiwoom_data.py`의 `kwcli` SDK (`import kiwoom`)와 `kiwoom_stream.py` 파서를 사용합니다. 국내/미국 시세 접근은 발급 환경·API 권한에 따릅니다. 인증 성공과 실제 스트림 수신은 별개 상태입니다. 이번 작업에서 키 인증·외부 시세 수신을 실행하지 않았습니다.

운영 설정은 `configs/local/operations.json`의 기존 `risk.fee/slippage`, `data.poll_seconds/timeout_seconds`, `symbols`, `expert_devices`입니다. 파일은 사용자 저장 요청 전에는 생성하지 않습니다. 기존 기본값은 가상 원장 fee 0.001/slippage 0.0001, 수신 주기 15초/대기 10초이며 SAC 설정 편집 API는 추가하지 않습니다. Expert 장치는 운영 풀과 이후 생성한 Registry에 적용됩니다.

## 실행과 의존성

- GitHub: `git clone --recurse-submodules https://github.com/hushmind3/continual-trading-agent.git`.
- Python 의존성: [requirements/operations.txt](requirements/operations.txt). 기존 설치 스크립트는 빠진 배포판만 설치하며 기존 패키지를 업그레이드하지 않습니다. FinRL·FinRL-Trading Git revision과 SB3·Torch 명세는 유지합니다.
- React 의존성: `frontend/package-lock.json`. 새 환경은 `frontend`에서 `npm ci`로 준비합니다.
- 운영: `서버켜기.cmd` → `scripts/start_server.py` → 8766 FastAPI 하나. 런처는 실제 cwd/명령/PID 소유권을 확인하고 이미 정상인 서버는 재사용합니다. 서버가 없을 때 기존 타입 검사·빌드 후 실행합니다.
- 개발: `frontend/start.cmd` 또는 `npm run dev` → 5173. 5173은 운영 런처에서 실행하지 않습니다.

```powershell
$env:PYTHONPATH="src"
$env:PYTHONUTF8="1"
.\.venv\Scripts\python.exe -m stockrl train --currency USD --symbols AAPL MSFT
.\.venv\Scripts\python.exe -m stockrl train --currency USD --symbols AAPL MSFT --resume
.\.venv\Scripts\python.exe -m stockrl backtest --currency USD --symbols AAPL MSFT
```

현재 작업 폴더에는 이전부터 `.gitmodules`, `SETTINGS.md`, `pyproject.toml`, `설치.cmd`의 미커밋 삭제 표시가 있습니다. 이번 커밋은 이 네 삭제를 포함하지 않습니다. GitHub에는 기존 버전이 유지됩니다. 로컬 설치 실행이 확인됐다고 기록하지 않습니다.

## 구현 상태와 보존 범위

- **소스 연결 완료 / 실제 실행 미확인**: React 운영 제어·KRW/USD 가상계좌·키움 인증/수신·외부 모델 조회/등록/적재/추론·검색/다운로드·변환/최적화·정책 선택 복원·운영 설정 API. 이번 변경에서 테스트·빌드·인증·시세 수신·모델 추론·학습·백테스트를 실행하지 않았습니다.
- **기존 연결 유지**: 공식 SAC 학습·Replay·백테스트·저장 가격 조회·FMP 수집·기존 동결 관측 구조. 새로운 실행 성공을 주장하지 않습니다.
- **미연결**: 실제 증권 계좌 주문, Alpaca 주문. **사용 조건 미충족**: 현재 저장된 이전 SAC는 원본 환경과 호환되지 않으며 SPY/필수 종목의 실제 이력이 없는 Expert는 입력 오류를 표시합니다.
- **제거한 실행 대상**: 루트 Streamlit 화면, 구형 화면 테스트/설정, 감사 보고서/임시 프론트 백업, 호출되지 않는 구형 operating_rules·package_disposal. 확인한 미사용 파일만 프로젝트 휴지통으로 이동했습니다. 공식 프레임워크와 정상 사용 모듈은 유지합니다.
- **배포 미적용**: 이번 작업에서 운영 서버를 재시작하거나 React `dist`를 다시 빌드하지 않았습니다. 현재 실행 중인 8766 서버의 코드와 정적 화면이 이 소스 버전이라고 주장하지 않습니다.

GitHub에는 React 소스·FastAPI/백엔드·기존 연결 모듈·공개 Registry/종목 설정·실행 스크립트·의존성·이 구조 설명을 보존합니다. `/data/`만 무시하므로 `frontend/src/data`의 `.ts/.tsx`는 추적합니다. 외부 모델 원본·가중치·가격/학습 실데이터·SAC/Replay·가상환경·node_modules·dist·로그·인증·휴지통은 업로드하지 않습니다. 외부 모델과 데이터를 별도로 준비해야 동일한 기능을 실행할 수 있습니다.
