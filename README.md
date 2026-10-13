# FinRL · SB3 + React — FinRL-X 보조

구조부터 확인: [백엔드 폴더 안내](backend/stockrl/README.md) · [프론트 폴더 안내](frontend/README.md). 각 기능 폴더의 README를 먼저 읽고 해당 진입점과 import/API 연결만 확인합니다.

React의 접이식 메뉴는 거래 운영·FinRL 메인·REA·프로젝트 확장·연결 관리의 5개 구역으로 구성합니다. FinRL 메인에는 정책 학습과 모듈·도구가 있고, 거래 운영·프로젝트 확장·연결 관리 기능을 별도 구역에서 제공합니다.


통합 소유자는 기존 `SystemOperations.system`입니다. 각 모듈의 JSON 결과 갱신을 보관하고 파일 버전이 바뀐 상태만 다시 계산합니다. `/api`의 `state` 요청는 현재 화면이 사용하는 조회 항목과 전체 운영·작업·모델·자원 상태를 함께 반환합니다. 조회 선택자는 공통 Context를 구독하며 개별 GET·별도 폴링을 하지 않습니다. 명령은 기존 POST API, 파일 전송은 결과 다운로드 경로를 사용합니다.

정책 인스턴스는 프로세스 내에서 체크포인트 절대 경로·파일 버전·알고리즘으로 캐시하며 변경 없는 모델은 재사용합니다. Champion Registry와 기본 ExpertPool도 재사용합니다. 신규 학습·작업은 기존 격리 프로세스를 유지하므로 학습 중인 가중치를 운영 추론에 공유하지 않습니다. 운영 제어는 운영 메뉴, 모델 선택·로딩은 정책 학습의 저장 모델 영역에서 한 번 제공합니다.


## 폴더와 진입점

```text
frontend/
  src/App.tsx                 메뉴 해시 라우팅
  src/shell/                  기존 화면 레이아웃
  src/pages/                  운영·MoE·시장·계좌·학습·연결·진단 화면
  src/pages/model/            Expert 등록·선택·적재·추론·변환·외부 폴더
  src/pages/training/         SAC 제어·Actor/Critic·체크포인트
  src/data/                   HTTP 요청·폴링·타입·Expert 분류
  src/ui/                     공통 Button·Panel·Drawer·표·상태·로그
  package.json / package-lock.json / vite.config.ts / tsconfig.json
  dist/                       운영 빌드 산출물, Git 제외
  node_modules/               설치 의존성, Git 제외
backend/stockrl/
  web_api.py / api_transport.py FastAPI 핸들러·단일 전달·유한 JSON·React 제공
  __main__.py / official_cli.py CLI → 현재 프레임워크 함수
  finrl/                      메인 FinRL·SB3 환경·학습·공식 데이터·평가
    framework.py              공식 환경·알고리즘·정책 경로
    operations.py             FinRL 실행 등록·주식거래 데이터/학습/평가
  finrl_trading/              공통 FinRL-X 가격·공급원 연결
    data.py                   기존 DataStore 가격 조회
    operations.py             추가 데이터·전략·공급원 실행 등록
  job_worker.py               별도 SAC/백테스트/수집 작업과 저장 기록
  platform/system_operations.py 통합 시작·중지·점검, 런처 적용 요청
  expert_registry_native.py   현재 Registry, 동결 추론, Expert별 64D 출력
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
    observations.py / expert_inference.py Expert 입력 생성·공통 추론 검증
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
scripts/install_windows.py      독립 주 환경·키움 SDK 환경 설치·정합성 검사
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

`main.tsx` → `OperationsProvider` → `App.tsx` → 화면 컴포넌트 순서입니다. `data/api.ts`의 `request()`가 `/api`를 호출하고 `OperationsProvider`가 `/api`의 `state` 요청를 주기적으로 읽습니다. 공통 상태에는 저장 정책·가격·동결 추론·자원·가상계좌·모델 작업 상태가 포함됩니다. 상태 조회는 학습·거래·다운로드를 시작하지 않습니다.

운영 8766은 `web_api.react_index()`와 `/assets`에서 `frontend/dist`를 제공합니다. 개발 5173은 Vite이며 `vite.config.ts`가 `/api`를 8766에 전달합니다.

| 메뉴 | 실제 HTTP 엔드포인트 (`/api` 접두사) | 호출 함수·소스 |
| --- | --- | --- |
| 운영 `#control` | GET state, POST controls/{feed,paper,engine} | `web_api.state`, `OperationsRuntime.command` |
| MoE `#moe` | GET state (모델·Library 통합 항목), POST experts/register, experts/select, library/{kind}, champions/create | `ExpertRegistry.register/select`, `model_files`, `LibraryOperations.start/_execute` |
| 연결 `#connection` | GET state (연결·인증·설정 통합 항목), POST provider/{connect,test,public}, settings | 기존 `connect_credentials/test_connection`, `operations_settings.update` |
| 진단 `#system` | GET state (로그·자원·모듈 통합 항목) | `ResourceMonitor.snapshot`, 실제 저장 로그·소스 함수 목록 |

다운로드는 단일 `/api`의 download/{name}으로 현재 SAC 정책·dataset 파일을 제공합니다. 체크포인트 다운로드는 GET `/api/checkpoint?path=...`입니다. 등록·선택·교체·해제는 같은 `configs/experts.json`의 슬롯/활성 목록을 사용합니다. 별도 Registry를 만들지 않습니다.

`library/{kind}` 작업: `inspect`, `import`, `probe`, `probe_all`, `load`, `unload`, `search`, `acquire`, `convert`, `optimize`, `optimize_all`, `apply`, `compare`. 작업 결과·진행·오류는 `runtime/operations/library-job.json`에 기록되어 React에서 표시됩니다. API 요청 수락과 실제 작업 성공은 구분합니다.

## 공식 프레임워크 역할과 학습 연결

| 프레임워크 | 현재 담당 |
| --- | --- |
| 설치된 FinRL | PortfolioOptimizationEnv, FeatureEngineer, DRLAgent·MODELS 알고리즘 선택, 학습·예측 호출 |
| FinRL-X (서브모듈 FinRL-Trading) | 보조 DataStore, 추가 데이터 처리·FMP 수집, StrategyResult, 비중 기반 BacktestEngine |
| 설치된 Stable-Baselines3 | SACPolicy/MlpPolicy, Actor/Twin Critic, Optimizer/Loss, Replay, 공식 save/load |

학습 경로:

1. React 주 학습 화면의 알고리즘·통화·종목·학습 단계 선택 → `preflight/train` → `/api/train` → `web_api.launch` → 별도 `stockrl.job_worker`. 알고리즘 목록과 공식 기본 설정은 백엔드 `/api/algorithms`가 설치된 FinRL에서 읽습니다. 기본 선택은 SAC입니다.
2. `official_cli.main` → `finrl_trading.data.prices(currency,symbols)` → 공식 DataStore의 실제 가격.
3. `finrl.framework.training_environment` → FinRL `data_split`의 기존 1,095일/365일 구간 → FinRL 원본 `PortfolioOptimizationEnv`. 기간 분할을 위해 FinRL-X RL 모듈을 import하거나 그 모듈의 전역 FinRL 예측 함수 교체를 실행하지 않습니다.
4. `ExpertObservation.observation` → `ExpertRegistry.outputs` → ExpertPool → 원본 관측을 펼친 값 + Expert별 실제 출력 64D + 계좌 상대값 16D.
5. `finrl.framework.train` → FinRL `DRLAgent.get_model(algorithm, MODEL_KWARGS[algorithm])`·`train_model` → 선택한 SB3 알고리즘. 이어 학습·백테스트·운영 로딩은 저장 메타데이터의 실제 알고리즘 클래스를 사용합니다. SAC Champion은 SAC에서 사용합니다.
6. 완료 시 `{algorithm}.zip`, `dataset.json`과 해당 알고리즘에서 사용하는 Replay를 저장하고 통화별 운영 정책으로 선택합니다. 작업 stdout 로그는 `runtime/official/jobs/`에 기록됩니다.

알고리즘 목록은 설치된 FinRL의 `MODELS`에서 읽으며 A2C·DDPG·PPO·TD3·SAC의 선택·생성·학습은 FinRL `DRLAgent`와 SB3가 담당합니다. 알고리즘 설정은 `MODEL_KWARGS`, 기본 학습 단계는 `DRLAgent.train_model` 인자 기본값에서 읽습니다. SAC가 기본 선택이며 SB3 정책 기본값과 PortfolioOptimizationEnv 기본값도 `source_settings()`가 설치된 클래스를 읽어 표시합니다. 통합 상태 조회의 기본 모듈 연결은 FinRL-X를 먼저 적재하지 않습니다. 보조 모듈은 해당 기능이 실제로 호출할 때 import하며 모듈 상태에는 프로세스의 실제 적재 여부를 기록합니다.

환경 인자는 기존 `finrl.framework.training_environment` 그대로입니다. 원본 Portfolio 환경의 `step()`은 포트폴리오 가치 환경이며 실제 증권사 체결이 아닙니다. PaperAccount는 별도의 기존 가상 원장입니다. 두 계층의 손익과 수수료 계산을 동일하다고 설명하지 않습니다.

## Replay · 정책 버전 · 백테스트

`job_worker`는 학습 실행 전에 현재 SAC·Replay·dataset을 `runtime/official/archives/{job_id}`에 보관합니다. `restore_checkpoint()`는 환경·예제 식별정보와 SB3 로딩을 확인한 뒤 `active-checkpoint.json`에 선택 경로만 기록합니다. 가중치 파일을 덮어써 복원하지 않습니다. `finrl.framework.policy_files()`가 선택한 폴더에서 정책·Replay·식별정보를 읽고, 이후 학습 결과는 현재 경로에 저장합니다. 현재 종목·통화와 맞지 않는 이어 학습은 기존 식별 검사를 사용합니다.


이전 `StockPortfolioEnv` 체크포인트와 Replay는 보존합니다. 새 `PortfolioOptimizationEnv` 계약으로 현재 선택된 11개 Expert와 AAPL/MSFT·USD·SAC 모델을 생성하고 105단계 진단 학습(실제 업데이트 5회)을 완료했습니다. 관측은 726D, 행동은 현금 포함 3D입니다. 기본 학습 단계 5,000은 유지하며 진단 학습 결과를 수익성 검증으로 설명하지 않습니다.

## 외부 모델과 Frozen Expert 계약

모델 기준 경로는 현재 사용자 `Desktop/모델`이며 저장소 안으로 강제 이전하지 않습니다. 실제 Expert 이름·역할·원본/양자화 구분·상대 파일명·SHA256·크기·종목·최소 이력·실행기는 [configs/experts.json](configs/experts.json)에 있으므로 여기서 동일 목록을 복제하지 않습니다.

- `expert-packages/*.pt`: `frozen_expert_package_v1`, `entry`, `state_dict`, `metadata`, `module_count`, `feature_size`. 구조 소스·원본 runner·입력 계약이 함께 있어야 합니다.
- GGUF JSON 패키지: 같은 패키지 형식, `executor=llama_cpp`, `weight_asset`가 실제 `.gguf` 상대 파일·크기·checksum을 참조합니다. 예: `expert-packages/qwen35_08b_gguf.json` → `expert-packages/444406ddd926550c724ec18d.gguf`.
- `champion.pt`: 확인한 형식은 `registered_vertical_trading_moe_v2`, 기존 12개 Expert 참조를 담습니다. 현재 SAC 중앙 정책으로 로드하지 않습니다. 필요한 Frozen Expert 참조만 선택 등록합니다.
- `experts/`의 개별 원본 가중치는 `native_upgrade.inspect_native/match_weights`가 기존 입력 템플릿과 실제 tensor 이름·크기를 대조합니다. 구조가 맞지 않는 파일은 구체적인 이유를 반환합니다.

등록 경로: 통합 상태의 models 항목 조회 → `library/inspect` 원본 계약 조회 → `library/import` 참조 등록 → 현재 Registry → `ExpertPool.get/run`. 외부 폴더의 기존 패키지는 참조를 등록하고 원본을 복사·수정하지 않습니다. 새로운 다운로드와 변환 결과는 기존 `expert-packages`의 별도 파일로 저장하며 원본과 구분됩니다.

입력은 `observations.native_input`의 완료 가격 시계열/OHLCV 또는 `StockPolicyExpert.prepare_input`의 원본 종목·지표·USD 계좌입니다. `expert_inference.prepare_inputs/run_batches`를 개별 검사·전체 검사·SAC 관측이 공유하며, 전체 검사는 입력의 모든 종목 묶음에 대해 출력 크기·유한값·종목 일치를 확인합니다. Chronos/TimesFM을 포함한 시계열 Expert는 실제 저장 시계열을 원본 예측 API에 전달하며 일봉·SPY 조건으로 실행 검사를 차단하지 않습니다. 입력 주기·출력 단위를 packet에 함께 기록합니다. 출력 packet은 `native_output`, `symbols`, `as_of`, `layout`, `units`를 갖고 관측 요약에 전달됩니다. 입력 부족·형식 불일치·실패는 오류/실패 기록으로 표시하며 결과를 만들어 채우지 않습니다.

실행기는 기존 `NativeExpert`, `StockPolicyExpert`, `HfForecastExpert`, `GGUFExpert`입니다. Torch·Transformers·Chronos·TimesFM·bitsandbytes·Accelerate·safetensors 및 llama.cpp 외부 실행기가 필요합니다. `llama_engine.ensure_engine`의 기존 실행기 준비 경로는 `runtime/.../engines`입니다. GGUF 가중치를 다시 다운로드하는 기능과 실행기 준비는 서로 다릅니다.

UI 적재는 `ExpertPool`과 기존 `Residency.preload/release`를 사용합니다. 현재 API의 적재 여부와 현재 자원 측정은 `current_resources/loaded`, 마지막 다른 학습 프로세스의 측정·출력은 `runtime/experts/status.json` 기록으로 구분합니다. 파일 크기를 RAM/VRAM 실측으로 표시하지 않습니다. 실제 추론은 사용자가 `probe`를 요청할 때 기존 실행기로 수행합니다.

검색·획득은 기존 HF/GitHub 검색과 tensor 구조·revision 확인 함수를 사용합니다. 변환은 기존 FP16/BF16/INT8/INT4/NF4 변환 함수, 최적화는 기존 품질 비교·정밀도 선택 함수를 호출합니다. 동일 실제 입력의 cold/warm 추론 측정은 사용자 요청 작업 안에서만 실행됩니다. 변환 및 최적화 작업을 이 복구 세션에서 실행하지 않았습니다.

## 시장 데이터 · 가상계좌 · 키움 · 운영 설정

`OperationsRuntime.command('feed',True)` → 기존 `LiveMarketCollector.run/collect_once` → 완료 Yahoo/Kraken 바 또는 `BrokerStreams` 키움 입력 → `AppendOnlyMarketCSV.append` → FinRL-X DataProcessor/DataStore → `OperationsRuntime.accept` → 기존 `PaperAccount.process_bar/save`. 과거 캐시 압축 코드를 공식 가격 DB에 적용하지 않아 기존 가격 이력을 지우지 않습니다. 실시간 입력은 수신한 완료 바 기준이며 저장 가격을 실시간 수신이라고 표시하지 않습니다.

가상계좌는 기존 독립 KRW 1,000만 원/USD 1만 달러 원장을 사용합니다. `manual_order`는 수신 시세 또는 실제 저장 가격을 명시하여 기존 `_fill`을 호출합니다. 보유·잔고·체결·실현/평가 손익과 pending 주문은 기존 원장 계산을 사용합니다. 시세 수신과 가상체결 활성화는 별도 제어입니다. 증권사에 실제 주문을 전송하지 않습니다.

SAC 자동 판단은 `OperationsRuntime.sac_decision` → 현재 원본 환경/ExpertObservation → `SAC.load/predict` → 환경의 원본 `softmax_normalization` → 기존 `PaperAccount.queue_decisions`입니다. 가상 원장 규칙이나 새 학습기를 구현하지 않습니다. 호환 정책·실제 관측이 없는 경우 `policy_error`를 표시합니다.

키움: 기존 `provider_credentials.connect_credentials/test_connection` → OS keyring 보안 저장소; 공급원·환경·마지막 인증 상태만 `configs/local/provider_settings.json`에 기록합니다. 시세 수송은 기존 `platform/kiwoom_data.py`의 `kwcli` SDK (`import kiwoom`)와 `kiwoom_stream.py` 파서를 사용합니다. 국내/미국 시세 접근은 발급 환경·API 권한에 따릅니다. 인증 성공과 실제 스트림 수신은 별개 상태입니다. 키움 SDK import와 정규화 이벤트 계약을 검사했고 키움 원격 인증은 실행하지 않았습니다. Yahoo/Kraken 시세 수신은 기존 운영 기록으로 확인합니다.

운영 설정은 `configs/local/operations.json`의 기존 `risk.fee/slippage`, `data.poll_seconds/timeout_seconds`, `symbols`, `expert_devices`입니다. 파일은 사용자 저장 요청 전에는 생성하지 않습니다. 기존 기본값은 가상 원장 fee 0.001/slippage 0.0001, 수신 주기 15초/대기 10초이며 SAC 설정 편집 API는 추가하지 않습니다. Expert 장치는 운영 풀과 이후 생성한 Registry에 적용됩니다.

## 실행과 의존성

- GitHub: `git clone --recurse-submodules https://github.com/hushmind3/continual-trading-agent.git`.
- Python 의존성: [requirements/operations.txt](requirements/operations.txt). 기존 설치 스크립트는 빠진 배포판만 설치하며 기존 패키지를 업그레이드하지 않습니다. FinRL·FinRL-Trading Git revision과 SB3·Torch 명세는 유지합니다.
- React 의존성: `frontend/package-lock.json`. 새 환경은 `frontend`에서 `npm ci`로 준비합니다.
- 운영: `서버켜기.cmd` → `scripts/start_server.py` → 8766 FastAPI 하나. 런처는 Git 추적 소스/미추적 소스의 내용 해시와 마지막 적용 기록을 비교합니다. 바뀐 React만 타입 검사·빌드하고, 백엔드 변경/서버 부재일 때만 소유권을 확인해 서버를 갱신합니다. 이후 CMD 기본 실행은 같은 전체 시작 API를 호출합니다.
- 개발: `frontend/start.cmd` 또는 `npm run dev` → 5173. 5173은 운영 런처에서 실행하지 않습니다.

```powershell
$env:PYTHONPATH="backend"
$env:PYTHONUTF8="1"
.\.venv\Scripts\python.exe -m stockrl train --currency USD --symbols AAPL MSFT
.\.venv\Scripts\python.exe -m stockrl train --currency USD --symbols AAPL MSFT --resume
```

현재 작업 폴더에는 이전부터 `.gitmodules`, `SETTINGS.md`, `pyproject.toml`, `설치.cmd`의 미커밋 삭제 표시가 있습니다. 이번 커밋은 이 네 삭제를 포함하지 않습니다. GitHub에는 기존 버전이 유지됩니다. 로컬 설치 실행이 확인됐다고 기록하지 않습니다.

## 구현 상태와 보존 범위

- **실제 실행 확인**: API·시세 입력·삭제 파일 캐시·GPU 계산·11개 Expert를 연결한 신규 SAC 진단 학습과 현재 등록된 화면 검사를 완료했습니다. 세부 범위는 검토 보고서에 기록합니다. 키움 원격 인증/전체 종목 수신·선택하지 않은 외부 모델 변환/최적화·정책 수익성은 검증 범위 밖입니다.
- **기존 연결 유지**: 공식 SAC 학습·Replay·백테스트·저장 가격 조회·FMP 수집·기존 동결 관측 구조. 새로운 실행 성공을 주장하지 않습니다.
- **미연결**: 실제 증권 계좌 주문, Alpaca 주문. **사용 조건 미충족**: 현재 저장된 이전 SAC는 원본 환경과 호환되지 않으며 원본 학습 종목·필수 지표의 실제 이력이 없는 주식 정책 Expert는 입력 오류를 표시합니다.
- **제거한 실행 대상**: 루트 Streamlit 화면, 구형 화면 테스트/설정, 감사 보고서/임시 프론트 백업, 호출되지 않는 구형 operating_rules·package_disposal. 확인한 미사용 파일만 프로젝트 휴지통으로 이동했습니다. 공식 프레임워크와 정상 사용 모듈은 유지합니다.
- **배포 상태**: `runtime/official/applied-sources.json`은 실제 적용된 소스/정적 파일 해시를 기록합니다. `apply.json`의 적용 단계와 `applied` 값으로 코드 반영을 확인합니다. 연결 점검의 준비 부족과 코드 적용 실패는 구분합니다.

GitHub에는 React 소스·FastAPI/백엔드·기존 연결 모듈·공개 Registry/종목 설정·실행 스크립트·의존성·이 구조 설명을 보존합니다. `/data/`만 무시하므로 `frontend/src/data`의 `.ts/.tsx`는 추적합니다. 외부 모델 원본·가중치·가격/학습 실데이터·SAC/Replay·가상환경·node_modules·dist·로그·인증·휴지통은 업로드하지 않습니다. 외부 모델과 데이터를 별도로 준비해야 동일한 기능을 실행할 수 있습니다.

## 통합 운영 자동화와 개별 제어

운영 화면에 `변경 적용 · 전체 점검`, `전체 시스템 시작`, `전체 시스템 중지`를 제공합니다.

MoE 화면은 등록 모델의 실제 버전 선택과 SAC Champion 조립에 사용합니다. `MoE Champion 생성`은 선택 알고리즘·모델과 기존 운영·학습 종목 구성을 `champions/create`에 전달합니다. Expert 선택과 마지막 생성 결과는 브라우저 세션에 유지하며 생성 결과에는 실제 중앙·결합부·Expert 파라미터, PT 크기, 선택 알고리즘의 관측/행동/정책·가치 차원과 MoE 구성을 표시합니다. 정책 학습 화면의 저장 모델 선택·로딩은 기존 `checkpoints/restore`를 사용하며 중앙 SAC를 실제 적재하고 통화별 `runtime/operations/policies.json`에 선택을 보관합니다. 운영 추론은 적재한 정책을 재사용하며 재시작 후 미로드 상태를 구분합니다. 명시적으로 선택한 정책은 자동 운영이 다른 모델이나 신규 학습으로 대체하지 않습니다. `전체 양자화`는 `library/quantize_all`, 각 카드의 `양자화`는 `library/quantize`를 사용해 기존 `convert` 함수로 가중치를 변환합니다. 이미 등록된 양자화 버전은 재생성하지 않습니다. 이미 양자화된 GGUF·PT는 실제 가중치 형식을 확인하여 기존 버전으로 기록하며 PyTorch Linear 재양자화를 시도하지 않습니다. 개별·전체 양자화는 기존 `measure`·`comparison_result`로 동일한 실제 입력 전체 묶음에 대한 원본/버전 출력을 비교합니다. 원본 입력·기준 출력은 Expert별 한 번 준비하고, 샘플링 모델은 같은 난수 상태로 비교합니다. 기존 버전도 재생성 없이 비교하며 출력 RMSE·상대 RMSE·MAE·최대 오차와 매매 판단 또는 예측 방향 일치도를 기록합니다. 비양자화 원본 없음·입력 부족·비교 실패는 가중치 생성 실패와 별도로 표시합니다. 최적 후보를 자동 선정하거나 비교 수치로 Champion 선택을 차단하지 않습니다. 카드에는 실제 FP32·FP16·BF16·INT8·INT4·NF4·GGUF 정밀도와 양자화 여부, 실제 파일/가중치 크기·변환 계층 수·처리 결과·실패 사유를 표시합니다. 모델 카드를 누르면 저장된 원본 출력 비교의 상대 RMSE·판단/방향 일치도·검사 시점을 기존 Drawer에서 확인합니다. 미측정 값은 미측정으로 구분하고 과거 변환 실패를 현재 가중치 파일 실패로 표시하지 않습니다. Toto의 `dd_unit_scaling.Linear` 하위 클래스는 원본 forward/scaling을 유지하며 압축 가중치를 읽도록 복원합니다. 카드의 선택 버전 삭제와 상단 선택 항목 삭제는 체크한 버전·실패 기록만 `library/remove`로 정리합니다. 선택하지 않은 원본·버전과 모델 파일은 보존합니다. MoE 선택 작업줄의 실행 버튼은 운영 Registry 적용(`experts/select`), 선택 버전 검사(`library/probe_all`의 ids), 메모리 로드·해제(`library/load`·`unload`), 원본 비교(`library/compare`의 ids)를 실행합니다. 검사 결과·입력 부족·실패·로드 상태와 비교 측정값을 기존 카드·결과 영역에서 표시합니다. 별도 정밀도 변환·자동 최적 후보 선정 화면은 사용하지 않습니다. 금융 Expert 검색·다운로드·가져오기, 작업 중지와 모델 폴더 열기는 기존 API를 유지합니다.

| 동작 | API / 실제 실행 경로 |
| --- | --- |
| 프론트/백엔드 독립 적용 | POST `/api/system/apply` → `start_apply` → 별도 일회성 `scripts/start_server.py --apply-only` |
| 진행 상태 | GET `/api`의 `state` 요청의 automation 항목 → `apply.json` + `SystemOperations.snapshot`; 재시작 전후 기록 유지 |
| 전체 연결 점검 | GET `/api/system/check` → 기존 설정·정책 메타데이터·Registry·원장·공급원·프로세스 조회 |
| 전체 시작 | POST `/api/system/start` → `SystemOperations.start/run`; CMD도 같은 API 호출 |
| 전체 중지 | POST `/api/system/stop` → 기존 runtime.command + 기존 SAC stop; 관리 서버 유지 |
| 모델 비교/작업 중지 | POST `/api/library/compare`, `/api/library/stop` → 기존 measure/comparison_result 및 작업 취소 요청 |
| 모델 폴더 열기 | POST `/api/model/open-directory` → 실제 외부 모델 폴더 (Windows) |
| 시세 연결 해제 | POST `/api/provider/disconnect` → 기존 수신 중지; 저장 인증 유지 |

변경 적용은 기존 `startup_lock`, 서버 소유권 확인과 런처를 재사용합니다. React 소스는 Git 추적·미추적 목록에서 선별하고 파일 내용 해시를 비교합니다. README/AGENTS 변경만으로 재빌드하지 않습니다. 공식 서브모듈 revision과 백엔드 소스 변경을 확인합니다. 변경이 없고 기존 산출물이 맞으면 빌드·재시작을 생략합니다. 새 관리 서버/상주 감시 프로세스/AI 운영 판단은 만들지 않습니다.

실행 중 SAC·모델 작업·시세·추론·가상매매·전체 시작이 있어도 서버 재시작이 필요 없는 React 프론트 변경은 빌드하여 반영합니다. 같은 시점에 백엔드도 변경됐다면 백엔드 재시작만 보류하고 프론트 적용 해시를 별도로 기록합니다. 서버 갱신 직전에 실행 중 작업을 다시 확인합니다. 준비 부족이나 실패를 적용 완료라고 기록하지 않습니다. 필요한 빌드 출력은 기존 runtime 로그에 저장하고 실패 단계에서만 오류 부분을 표시합니다. 별도 테스트/감사 보고서는 만들지 않습니다. 브라우저 테스트나 벤치마크를 자동 실행하지 않습니다.

전체 시작은 기존 KRW/USD 원장 로딩 → 사용자 선택 Expert 적재 → 통화별 정책 호환 확인 → 필요할 때만 저장 데이터로 공식 SAC 학습 → 저장 인증/실시간 시세 확인 → 실제 입력 추론/가상체결 순서입니다. 시세 수신에 실패해도 앞선 SAC 학습 결과는 보존하며, 실제 시세가 없으면 추론·가상매매는 시작하지 않고 보류로 표시합니다. 운영 화면에서 두 통화 또는 한 통화를 선택할 수 있습니다. 학습 데이터/모델/시세가 부족한 통화는 원인을 표시합니다. 호환 정책이 있으면 새 학습을 하지 않습니다.

학습 결과는 `runtime/official/policies/{job_id}/`에 별도 저장하며 자동으로 운영 정책에 승격하지 않습니다. 정책 학습의 `저장 모델 → 모델 로드`가 기존 `checkpoints/restore` API를 통해 사용자가 선택한 모델만 `runtime/operations/policies.json`에 기록합니다. 전체 시작과 추론은 승인된 정책만 사용하며, 정책 미승인은 오류로 표시합니다. 수수료·슬리피지·기간 외 검증·MDD·Sharpe 등의 자동 성과 합격 기준은 설정하지 않았습니다.

React의 상태 조회·버튼 명령·파일 다운로드는 단일 `/api` 통로로 전달합니다. JSON 요청은 `POST /api`에 `{operation, payload}`를 보내며, 이미지·파일은 같은 `/api`의 GET 요청에 `operation`과 `payload`를 전달합니다. 실행 기능은 백엔드 내부 라우터에서 원래 모듈 함수를 호출하고 개별 `/api/...` 경로는 공개하지 않습니다. 서버 적용 스크립트도 동일 통로를 사용합니다.

통합 JSON 응답은 클라이언트가 지원하면 gzip으로 압축합니다. 통합 상태는 모듈 조회 실패 시 마지막 성공 값과 `module_errors`·`module_updated_at`을 함께 반환하고 다음 요청에서 재시도합니다. 초기 실패는 해당 값이 `null`이며 관련 화면에 오류를 표시합니다. 외부 인증·실행 상태는 매 요청에서 조회하며 저장 모델과 정책 목록은 관련 파일 변경으로 갱신합니다. 승인 정책과 마지막 작업 모델만 캐시에 유지하고 이전 작업 모델은 오래된 사용 순서로 해제합니다. 정책 승인 변경과 서버 종료에도 모델 캐시를 정리합니다. 학습 프로세스의 메모리는 API 서버와 별개입니다. 환경 종료는 환경만 닫고 공유 Expert Registry를 유지합니다. Registry와 모델 해제는 통합 관리자가 담당하며 CLI 종료도 동일 정리 경로를 사용합니다. 공식 callable의 필수 인자·인자명은 작업 프로세스를 만들기 전에 확인하고 오류를 화면에 반환합니다. 단일 상태 요청에서 필요한 FinRL·FinRL-X·Expert·시세 모듈의 실제 백엔드 import를 연결하고 성공 결과를 재사용합니다. `imports`는 import 결과를 표시하며 실행 성공과 구분합니다. 과거 실패는 최신 같은 모듈 작업의 성공 뒤에 현재 오류로 남기지 않습니다. 엔진·지속학습 시작은 승인 정책의 통화·경로·공식 환경·공간 계약을 먼저 확인합니다. 모델 적재 표시는 통합 관리자의 실제 캐시를 기준으로 하고, 의도적으로 중지된 시세는 실행 대기로 구분합니다. JSON 기록은 파일별 프로세스 잠금과 고유 임시 파일로 직렬화하고 작업 시작·완료·중지는 잠금 안에서 읽고 갱신합니다.

운영 풀에 적재한 Expert는 기존 `ExpertRegistry`에 pool provider를 전달해 관측 추론에서 공유합니다. 기존 출력 요약·환경·관측 차원은 그대로입니다. 개별 제어가 자동 시작과 충돌하면 자동 절차는 중단 사유를 표시하고 사용자 명령을 우선합니다. 전체 중지는 기존 학습 중지와 시세/추론/가상체결 중지를 사용하며, 진행 중인 네이티브 연산의 종료 대기와 실제 중지 완료를 구분합니다. 실제 증권사 주문은 호출하지 않습니다.

바탕화면 `서버켜기.cmd`는 프로젝트 루트의 같은 CMD로 전달하는 실행 진입점입니다. 다른 PC에서는 해당 루트 CMD의 바탕화면 바로가기를 사용할 수 있습니다. 루트 CMD → 기존 런처 → 변경 적용/상태 조회 → 같은 전체 시작 API 순서입니다. 서버가 이미 켜져 있어도 소스 변경을 적용합니다. `--apply-only`는 전체 운영을 시작하지 않습니다.

시장·운영 화면의 시세 수신·자동 판단·가상매매 버튼은 상단에 배치합니다. 운영 화면의 `코드 변경 적용`은 기존 React 빌드·8766 서버 갱신·연결 상태 조회이며 오류 자동 복구가 아닙니다. `자동 운영 시작`은 기존 system/start 절차로, 호환 정책 준비(정책이 없으면 SAC 학습) 이후 시세 수신·판단·가상매매를 시작합니다. 개별 제어와 실행 결과는 같은 상단 운영 패널에 표시합니다.

운영의 실시간 SAC 지속학습 버튼은 완료 시세가 저장되는 기존 `accept` 경로에서 선택 통화의 SAC 이어 학습 작업을 요청합니다. 기존 공식 설정·Replay 복원 경로를 사용하며 진행 중 작업은 대기하고 새 정책/Champion 버전으로 저장합니다. 끄기와 전체 중지는 이 버튼으로 시작한 학습만 중지합니다. 실제 시세·학습 성공은 런타임 상태·작업 로그로 확인해야 합니다. KRW/USD 학습은 통화별 선택 정책을 사용합니다. 기존 전역 결과 파일과 체크포인트는 보존합니다.

## 공식 시스템 이식 · React 실행 메뉴

`#frameworks`는 Python 모듈을 브라우저에서 import하지 않습니다. React → `/api/framework/{action}` → 기존 `job_worker` → `platform/framework_operations.py` → `finrl_trading/operations.py` 또는 원본 native_call → 공식 Python 함수·클래스·CLI 순서입니다. Streamlit 화면은 이식·실행에서 제외합니다.

FinRL 알고리즘 선택은 주 학습 화면과 기존 학습 API에 통합합니다. 별도의 알고리즘 학습 도구는 두지 않습니다. FinRL-Trading 보조 메뉴의 거래 달력·전략·재무/뉴스·CSV·ML·평가 및 deploy 실행 어댑터는 제거했습니다. FinRL-X의 공통 가격 저장·수집·공급원 인증과 공통 원본 함수 호출은 남은 기능에서 사용합니다. FinRL·SB3는 백엔드 Python에서 import·실행하며 React는 API 설정·목록·상태·결과를 표시합니다.

나머지 공식 공개 callable은 백엔드의 `/api/framework/native_call`에서 실제 소스 선언·인자 계약에 따라 호출합니다. 동일 인스턴스의 메서드 연결, 원본 CLI 인자, 실제 DataFrame/Series/배열·설정 참조를 전달할 수 있습니다. 필요한 인자·객체·패키지·인증이 없으면 실제 오류를 반환하며 실행 성공으로 표시하지 않습니다. 모델 생성자 호출과 학습·추론 성공은 구분합니다.

통합 상태의 framework 항목은 두 공식 프레임워크의 실제 설치 소스·함수·입력 계약·의존성·호출을 조회합니다. 상태와 성공 함수는 실제 작업 기록으로 구분합니다. 모든 함수의 실행 성공을 보장하는 목록이 아닙니다. 작업·로그·전체 JSON/CSV·원본 그래프는 `runtime/official/framework-jobs/{job_id}`에 저장하며 `/api/stop`으로 동일 작업과 자식 프로세스를 중지합니다.

연결 메뉴의 FMP·Alpaca·WRDS 값은 기존 OS keyring에 저장하고 공식 작업의 원본 환경변수로 전달합니다. 저장 여부와 인증·시세 성공은 구분합니다. 기타 공급원은 원본 생성자·외부 설정 계약을 요구합니다. Expert 최적화·변환·허용 기준은 기존 `library` API와 연결했고 모델 폴더 목록은 통합 상태의 models 항목을 사용합니다.

이미 빌드한 화면을 적용하고 추가 검증을 생략하도록 기존 `scripts/start_server.py.main`에 `skip_build`, `skip_checks` 선택 인자를 추가했습니다. 기존 기본 실행 동작은 동일합니다.


## 백엔드 배치와 소유권

자체 Python 코드는 `backend/stockrl/`에 모읍니다. React는 `frontend/`, 공식 보조 원본은 `FinRL-X/`, 저장 상태·작업 결과는 기존 `runtime/`, 데이터와 모델 자산은 기존 경로를 사용합니다. Python 모듈 이름 `stockrl.*`은 유지합니다.

- `web_api.py`: 핸들러·요청 검증·React 제공
- `api_transport.py`: 단일 통로·응답 전달·유한 숫자 JSON
- `platform/system_operations.py`: 통합 상태·정책 캐시·Registry·작업 프로세스·실행 및 중지
- `platform/operations_runtime.py`: 시세·추론·계좌 실행; 학습 작업은 통합 관리자에 전달
- `finrl/framework.py`: 공식 환경·학습·정책 계약
- `finrl_trading/`: 보조 저장·비중 평가·추가 실행
- `state_io.py`: 프로세스 간 상태 기록

상태 조회는 통합 관리자의 모듈 캐시를 사용하고 정책 변경은 공통 작업 잠금으로 직렬화합니다. 잠금 순서는 작업→운영→모델로 맞춥니다. 선택한 Champion은 백테스트에 실제 전달하며 학습의 로딩·등록·저장에서는 한 번 읽은 Spec을 공유합니다. Champion 목록·검사는 가중치를 보관하지 않고 파일 버전별 메타데이터만 재사용합니다. Expert 결과 캐시는 입력·계좌가 같을 때만 재사용하고 통화·Expert별 마지막 입력만 유지합니다.

학습 전 검사는 실제 학습·추론이 읽는 동일 가격 모듈로 rolling 구간의 종목별 가격 행렬을 확인합니다. 누락 가격을 만들거나 종목을 자동 제외하지 않습니다. 추론은 선택 종목의 최신 바가 모두 도착할 때까지 대기하고 통화별 처리 시각으로 중복 판단을 막습니다.

프론트만 적용할 때는 기존 scripts/start_server.py --apply-only --frontend-only를 사용합니다. 단일 API의 system/apply 명령은 target이 frontend(기본값), backend, all 중 하나입니다. 프론트 적용 시 백엔드 변경이 남아 있어도 서버를 재시작하지 않으며, 통합 상태의 frontend_revision 변경을 브라우저가 반영합니다.

## 데이터·계좌 정합성과 CI 검사

가상계좌는 종목별 마지막 처리 시각으로 봉·체결 중복을 막습니다. 학습과 운영의 16개 계좌 관측은 해당 초기자본으로 정규화하며, 운영 보유 비중·낙폭·변동성은 실제 원장의 평가 시세와 관측 이력으로 계산합니다. 모델 관측 종목 밖의 보유량은 누락하지 않고 입력 오류로 표시합니다. 기존 원장의 과거 평가 이력을 새로 만들어 채우지 않습니다.

수신 분봉·시세는 CSV와 received_bars 인덱스에 보관하고, 완료 일봉만 공식 가격 저장소에 공급합니다. 가격 조회는 완료 일봉 저장소를 우선하며 분봉으로 확인된 행은 학습에서 제외합니다. 구분되지 않는 상충 일봉은 오류로 반환합니다. 모든 종목이 갖춰진 가장 최근 공통 일봉으로 추론하며 저장 성공·중복 제거를 통과한 행만 원장에 전달합니다. 시세 수신과 추론은 별도 스레드이고, 같은 일봉 데이터 버전으로 지속학습을 반복하지 않습니다. 수동 즉시 체결은 기존 수신기의 5분 최신 시세 기준을 사용합니다.

GitHub backend-integrity CI는 Python 3.13 구문·정합성·FastAPI 전송과 Node 22 React 타입·빌드·전송 회귀를 실행합니다. 실제 GPU 정책 성능과 전체 백테스트는 로컬에서 별도 검증합니다.

시세 공급원별 없는 선택 필드는 `None`으로 처리하며 API 응답의 비정상 숫자는 `null`로 전달합니다. 외부에서 삭제한 Champion 파일의 상태·오류 캐시는 다음 통합 조회에서 제거합니다. 회귀 검사에는 혼합 시세 필드의 JSON 정합성과 삭제된 Champion 오류의 제거를 포함합니다. 전체 검토의 확인 결과·남은 차단 사항·검증 범위는 [프로젝트 검토 보고서](프로젝트_검토보고서.md)에 기록했습니다.

CI 워크플로가 main에 설치되기 전에는 수신기가 waiting_for_main_workflow로 대기하며, Issue별 수정 실행·직접 배포를 시작하지 않습니다.

학습과 MoE의 알고리즘 선택값은 공유합니다. MoE는 설치된 FinRL 목록에서 선택한 A2C/DDPG/PPO/TD3/SAC/TQC/CrossQ의 공식 정책을 생성하고 해당 알고리즘으로 새 버전 학습합니다. 새 학습은 이전 저장 모델의 호환 여부를 요구하지 않으며 Replay는 지원하는 알고리즘만 저장합니다.

## 재현 환경과 자동검증

주 `.venv`와 키움 `.venv-kiwoom`은 시스템 패키지를 공유하지 않습니다. 설치 스크립트는 운영/키움 명세와 lock 제약을 적용하고 양쪽 `pip check`를 실행합니다. 주 Torch 2.14.0+cu132·torchvision 0.29.1+cu132·SB3 2.9.0과 FinRL 고정 커밋을 유지합니다. 키움 SDK는 별도 프로세스의 JSON 이벤트로 수집기에 연결해 Alpaca/키움 websockets 버전 충돌을 해소합니다. FinCast 실행에 필요한 beartype/einx/colt5-attention도 명시합니다. 미사용 이전 환경은 사용자 지시에 따라 `휴지통/.venv-previous-20261012-232811/`로 이동했습니다. 휴지통은 실행 경로에 연결하지 않습니다.

Python 3.13에서 `python -m unittest discover -s tests`는 정합성 21개와 실제 FastAPI 전송 3개를 검사합니다. React 타입·빌드와 전송 테스트 4개는 CI에서도 실행합니다. 로컬 서버의 실제 현재 등록된 화면 검사는 `frontend`에서 `npm run test:browser`로 실행합니다. GPU 모델·외부 인증은 이 최소 CI의 범위에 포함하지 않습니다. 자세한 실행 근거와 제한은 기존 [검토 보고서](프로젝트_검토보고서.md)를 확인하세요.

2026-10-13 실행 검증: 신규 SAC의 11개 Expert 모두 CUDA 추론, 105단계 진단 학습·업데이트 5회, 평가 251개 거래일과 공식 가치·지표 저장을 완료했습니다. 현재 USD 선택은 추가 작업 전 `champions/sac_champion_003/sac.zip`으로 복원했으며 구형 모델·Replay와 이전 선택 경로는 보존합니다. 원본 BacktestEngine의 가중치 이력·거래 DataFrame은 비어 있으므로 해당 표를 체결 내역으로 취급하지 않습니다.

## 현재 FinRL 메뉴 범위

FinRL 메인은 정책 학습과 FinRL 모듈·도구 2개 작은 메뉴를 제공합니다. 정책 평가·백테스트, 주식거래 데이터 준비·알고리즘 학습·백테스트, FinRL 원형 학습·평가·모의매매, Yahoo 수집, 기술지표·전처리, 기간 분할, 백테스트 성과의 9개 메뉴와 전용 화면·실행 어댑터·평가 API/CLI·결과 조회를 제거했습니다. 공통 FinRL/SB3 학습·정책 구조와 가상계좌·시세·Expert 경로는 유지합니다. 전체 기본 작은 메뉴는 11개입니다. 폐기 소스는 휴지통에 동일 상대 경로로 보존하며 저장 모델·가격·계좌·기존 산출물은 삭제하지 않습니다.

FinRL-Trading 큰 메뉴와 보조 화면 6개를 제거했습니다. 전용 메뉴 등록·화면·Adaptive Rotation 원형 실행 3개·거래일·설정 검사 어댑터와 기존 13개 추가 기능은 제공하지 않습니다. 공통 가격 조회·수집·인증과 공식 원본은 남은 기능의 의존성으로 유지합니다.

## REA 역공학

프로그램 분석(파일 선택·폴더 선택·웹사이트 분석)과 프로젝트 탐색 두 작은 메뉴를 제공합니다. 백엔드 모듈은 backend/rea, 프론트는 frontend/src/pages/rea, 실제 결과는 Git에 포함하지 않는 backend/rea_projects/<ID>에 저장합니다. original/ 원문·원본 파일, inferred/ 추론·의사코드, analysis/ 구조·함수·모듈·근거를 구분해 사용자 버튼으로 저장 폴더를 엽니다. 코딩 에이전트 호출·자동 재구현·추출 프로그램 실행은 연결하지 않습니다. 자세한 범위는 [REA 백엔드](backend/rea/README.md)를 확인하세요.
