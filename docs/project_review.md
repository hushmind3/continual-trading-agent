# 프로젝트 전체 검토 보고서

검토일: 2026-10-12, 수정·실행 검증 갱신: 2026-10-13 (한국 시간). 검토 대상: 현재 로컬 프로젝트. 기준 이력은 `fcd3f37` 상태를 복원한 `32569b8`, 통합 API 숫자 처리 수정 `40b3049`, 그리고 이번 삭제 파일 캐시 수정이다.

## 1. 결론

프로젝트의 역할 구분은 실제 코드에 존재한다. React의 메뉴 관리자, 단일 HTTP 통로, 공통 상태·작업·모델 관리자, FinRL 학습 경로, FinRL-Trading 보조 경로, Expert 실행 계층, 시세 수신과 가상계좌는 서로 다른 책임을 가진다. 그러나 소스 복원만으로 실행 프로세스·메모리 캐시·기존 체크포인트·설치 패키지가 같은 버전으로 돌아가지는 않는다. 앞선 복구 확인은 이 구분을 충분히 검증하지 못했다.

현재 통합 API 조회는 정상이며 삭제된 Champion 파일의 오류도 제거됐다. 구형 저장 정책은 보존하고 현재 계약으로 신규 모델을 생성했다. 독립 실행 환경과 SDK 프로세스 분리로 설치 충돌을 해소했으며 실제 학습과 화면 검사를 수행했다. 검증 범위는 아래 결과에 한정한다.

## 2. 검토 범위와 방법

검토 시작 시 Git 추적 대상은 187개였다. Python 84개, TSX 45개, TS 14개, 프로젝트 Markdown 27개와 설정·실행 스크립트·CI를 분류했다. 백엔드 파일 89개, 프론트 `src` 파일 75개를 대상으로 구조를 확인했다. Python 전체 구문·정의 목록과 상대 import, 프론트 상대 import·API 사용, 프로젝트 문서의 연결·역할을 점검하고 아래 실행 경로의 실제 구현을 추가 확인했다.

| 영역 | 확인한 구현과 연결 |
| --- | --- |
| 진입점·실행 적용 | `서버켜기.cmd`, `scripts/start_server.py`, `scripts/install_windows.py`, `stockrl.__main__`, `official_cli`, `job_worker` |
| React 구조 | `App`, `Shell`, 큰 메뉴 관리자 5개, 화면·공통 UI·상태 Provider |
| 단일 API | `web_api`, `menu_registry`, 메뉴별 백엔드 연결 파일, 입력 계약·응답 직렬화 |
| 공통 관리 | `SystemOperations`의 상태·오류·파일 서명·작업·정책·Registry 캐시 |
| 학습·평가 | `finrl/framework.py`, `finrl/operations.py`, FinRL-Trading 가격 조회·비중 평가 |
| MoE | `sac_champion`, `ExpertObservation`, 생성 형식·알고리즘·관측/행동 계약 |
| Expert | Registry·Pool·입출력 계약·패키지·원본 실행·장치·적재·검사·변환·라이브러리 작업 |
| 시장 데이터 | Yahoo/Kraken/키움 수신, 중복 방지 저장, 완료 바·일봉 구분 |
| 가상계좌·운영 | 통화별 원장·비용·주문·다음 완료 바 체결·운영 추론·지속학습 |
| 설정·인증 | 종목·Expert 설정, 운영 설정, 공급원 상태, OS keyring 사용 |
| 문서·환경·검증 | 루트/하위 README·SETTINGS, 의존성 명세와 실제 설치 버전, 테스트·CI |

외부 FinRL-X 원본, 모델 가중치·Replay·계좌 기록·인증 값은 수정하거나 Git에 추가하지 않았다. 외부 프레임워크는 설치 버전·고정 커밋·호출 계약을 확인했으며 원본 전체에 대한 줄 단위 감사를 수행한 것은 아니다. 프로젝트 전체의 정적 점검과 주요 경로 검토를 모든 함수의 실제 실행 검증으로 설명하지 않는다.

## 3. 실제 구조와 소유권

### 3.1 화면 → API → 기능

현재 큰 메뉴는 거래 운영 3개, FinRL 메인 6개, FinRL-Trading 보조 1개, 프로젝트 확장 2개, 연결·관리 3개로 **5개 구역 / 기본 작은 메뉴 15개**다. 백엔드 등록 정보에 따라 추가 기능을 연결한다. 검토 시 `menu_catalog`에는 큰 메뉴 5개, action 27개, command 59개가 반환됐다. 등록 개수는 실제 기능 실행 성공을 의미하지 않는다.

`OperationsProvider`가 화면의 조회 항목을 모아 `state`를 요청한다. `data/api.ts`가 `operation`·`payload`를 단일 `/api`로 전송하고, `api_transport.UnifiedAPI`와 `menu_registry.dispatch`가 등록된 내부 핸들러로 전달한다. 백엔드 상태 관리자는 `SystemOperations`이며 `/api`는 그 HTTP 어댑터다. 프론트가 화면별로 따로 백엔드 상태를 소유하는 구조가 아니다.

근거: [OperationsProvider](../frontend/src/data/Operations.tsx), [API 전송기](../frontend/src/data/api.ts), [요청 분배](../backend/menu_registry.py), [HTTP 어댑터](../backend/web_api.py).

### 3.2 학습·MoE·Expert

주 정책 경로는 `job_worker → official_cli → finrl.framework.train → FinRL DRLAgent → SB3`다. 환경은 현금 포함 `PortfolioOptimizationEnv`이고 Shimmy와 `ExpertObservation`으로 연결한다. 가격 관측 뒤에 **Expert별 실제 출력 64D + 계좌 16D**를 붙이며 `ChampionExtractor`가 공식 알고리즘의 정책·가치 입력에 연결된다. 이 결합부는 프로젝트 구현이며 SB3 기본 구조 전체를 그대로 사용한다는 설명은 정확하지 않다.

MoE 생성과 학습에는 설치된 FinRL의 A2C/DDPG/PPO/TD3/SAC/TQC/CrossQ 목록과 알고리즘별 설정을 사용한다. 기본 단계는 5,000이며 요청으로 변경 가능하다. Replay는 해당 기능을 지원하는 알고리즘에서 저장한다. Expert 가중치는 동결하고 Registry·Pool을 통해 재사용한다. 메타데이터 목록 조회, 메모리 적재, 실제 Expert 추론은 서로 다른 작업이다.

별도 주식거래 메뉴는 공식 `StockTradingEnv` 예제 경로다. 이 결과를 MoE의 현금 포함 환경과 호환 모델로 취급하지 않는다. FinRL-Trading은 `DataStore`, 공급원·전략과 `StrategyResult/BacktestEngine` 평가를 보조한다.

근거: [주 학습·백테스트](../backend/stockrl/finrl/framework.py), [관측 계약](../backend/stockrl/expert_observation.py), [Champion 생성·형식](../backend/stockrl/platform/sac_champion.py), [현재 FinRL 메뉴 연결](../backend/stockrl/finrl/finrl_menu_manager.py).

### 3.3 실행 상태·저장 상태

현재 소스, 실행 중 서버가 적재한 코드, 프로세스 내 상태 캐시, `runtime`의 저장 기록, 모델 폴더의 PT, 실제 SB3 체크포인트 ZIP, 설치된 라이브러리는 각각 다른 상태다. Git 복원은 Git 추적 파일을 복원한다. 제외된 데이터와 모델을 되돌리지 않으며 이미 떠 있는 프로세스도 자동으로 바꾸지 않는다.

Champion PT는 구성·정체성·체크포인트 참조를 가진 Spec이다. PT를 삭제해도 별도의 ZIP·`dataset.json`·Replay를 자동 삭제하지 않는다. 이번 검토에서도 삭제된 PT를 참조하는 구형 정책의 저장 메타데이터가 존재했다. 따라서 “삭제한 PT의 오류 캐시”와 “남아 있는 ZIP의 실제 비호환”은 다른 문제다.

시세 수신은 운영 스레드가 담당하고 정책 추론·지속학습은 별도 경로다. 자동 정책 결정과 가상 체결은 제어 상태와 승인 정책을 요구한다. `PaperAccount`는 실제 증권사 주문이 아닌 가상 원장이며 같은 관측 바에서 주문을 체결하지 않도록 다음 완료 바 계약을 적용한다.

## 4. 확인된 문제와 처리 결과

### F1. 시세의 NaN이 통합 응답 전체를 실패시킴 — 수정·실행 확인

공급원별 선택 필드가 다른 행을 DataFrame으로 합치면 없는 `bid/ask/trade_count` 등이 `NaN`이 될 수 있었다. 시세 상태에 포함된 `NaN`을 JSONResponse가 직렬화하지 못해 HTTP 500을 반환했다. 프론트는 이를 `통합 API 연결: 서버 응답을 읽을 수 없습니다.`로 표시했다. 상태를 한 번에 받는 구조이므로 한 숫자의 직렬화 실패가 여러 화면에 영향을 줬다.

`OperationsRuntime.accept`에서 결측값을 `None`으로 처리하고 API JSON 응답에서는 비정상 실수를 `null`로 바꾸도록 수정했다. 저장 가중치·계좌 값을 응답 변환으로 덮어쓰지 않는다. 혼합 공급원 회귀 검사와 중첩 NaN/무한대 응답 검사에 통과했다. 시세 수신을 켜고 5회 반복 조회하는 동안 신규 시세 수가 37→44로 증가했고 모두 HTTP 200과 엄격한 JSON 파싱에 통과했다.

근거: [시세 수신 상태](../backend/stockrl/trading/control/operations_runtime.py), [FiniteJSONResponse](../backend/api_transport.py). 반영 커밋: `40b3049`.

### F2. 삭제한 Champion의 과거 형식 오류가 계속 표시됨 — 수정·실행 확인

`champion_info`는 파일별 `champion:<절대경로>` 상태와 실패를 `SystemOperations`에 기록한다. 파일이 삭제되면 목록에서는 빠지지만, 해당 키의 과거 오류를 재평가하거나 지우는 경로가 없었다. 실제 로컬 폴더에 PT 3개가 없는데도 오류 3개가 API에 계속 남아 있었다.

통합 상태 조회와 Champion 목록 조회에서 사라진 파일의 상태·서명·오류·갱신 시각을 제거하도록 수정했다. 파일이 실제로 존재하는 형식 오류나 다른 모듈의 오류는 보존한다. 임시 파일로 삭제 전후·반복 조회·다른 오류 보존을 검증했고, 삭제 캐시 수정 당시 실행 서버에서는 Champion 목록 0개와 `module_errors={}`를 확인했다. 후속 검증에서는 새 Champion을 생성했다.

추가로 Champion 목록의 파일 서명이 `sac_champion_*.pt`만 추적하고 실제 목록은 `*_champion_*.pt`를 읽는 불일치를 확인했다. 목록 서명도 전체 알고리즘 패턴으로 맞춰 외부에서 추가·삭제한 비-SAC Champion도 다음 조회에 반영하도록 수정했다.

최종 실행 검사에서는 검증용 비-SAC PT를 잠시 만들어 형식 오류가 발생하는 것을 확인한 뒤 그 파일만 삭제했다. **서버 PID를 그대로 유지한 상태에서 다음 조회의 오류가 제거됐다.** 단순 재시작으로 캐시가 초기화된 결과와 구분되는 검증이다. 검증용 PT는 정리했으며 기존 모델은 수정·삭제하지 않았다.

근거: [캐시 수명 관리](../backend/stockrl/platform/system_operations.py), [Champion 목록](../backend/stockrl/platform/sac_champion.py), [회귀 검사](../tests/test_state_integrity.py).

### F3. 저장 정책과 현재 프로젝트 환경·입출력 계약 불일치

시스템 정책 점검과 백테스트 사전 검사에서 다음 차이를 실제 확인했다.

| 항목 | 저장 정책 | 현재 검사 계약 |
| --- | --- | --- |
| 환경 | `StockPortfolioEnv` | `PortfolioOptimizationEnv` |
| 관측 / 행동 | `[996]` / `[2]` | `[982]` / `[3]` |
| SAC 배치 | 128 | 64 |
| SAC 학습률 | 0.0003 | 0.0001 |

위 관측 수는 해당 저장 정책의 종목·Expert 정체성을 기준으로 계산한 검사값이며 모든 신규 모델의 고정 차원이 아니다. 현금 행동의 추가와 관측 계약 변경을 파일 이름이나 형식 태그만 바꿔 해결할 수 없다.

`preflight/train`의 **새 학습**은 AAPL/MSFT, USD, SAC로 `ok=true`였다. 반면 동일 종목의 `preflight/backtest`는 구형 환경·공간 비호환을 이유로 `ok=false`였다. API 연결은 정상이어도 기존 정책 백테스트와 전체 운영 준비가 차단될 수 있다. 후속 수정에서 선택된 11개 Expert와 AAPL/MSFT·USD·SAC의 신규 `sac_champion_007.pt`를 생성하고 105단계 진단 학습·실제 업데이트 5회를 완료했다. 관측 726D·현금 포함 행동 3D다. 구형 가중치·Replay는 삭제·변환하지 않았다.

근거: [정책 계약 검사](../backend/web_api.py), [전체 점검](../backend/stockrl/platform/system_operations.py), [환경·학습 연결](../backend/stockrl/finrl/framework.py).

### F4. 설정·관측 설명이 실제 코드와 다름 — 기존 문서 정정

`SETTINGS.md`는 과거 FinRL-X `train_sac`, 50,000단계, 배치 128, 학습률 0.0003, `StockPortfolioEnv`, 8개 요약 신호를 현재 경로로 설명하고 있었다. 실제 API와 코드의 값은 DRLAgent, 기본 5,000단계, 배치 64, 학습률 0.0001, `PortfolioOptimizationEnv`, Expert별 64D + 계좌 16D였다.

기존 `SETTINGS.md`의 관련 표·설명·출처를 정정하고 루트 README의 8개 신호 설명도 수정했다. FinRL 알고리즘 설정, SB3 자체 기본값, 프로젝트 결합부·환경 지정값을 구분했다. 삭제 캐시와 숫자 처리의 동작·검사는 기존 백엔드 문서와 README에도 반영했다.

근거: [현재 설정](settings.md), [프로젝트 기준 문서](history.md).

### F5. 설치 환경 요구 버전 불일치 — 수정·실행 확인

기존 시스템 패키지 공유 환경의 충돌 15개를 확인하고 주 `.venv`와 키움 `.venv-kiwoom`을 독립 환경으로 분리했다. 주 FinRL의 Alpaca websockets<11과 키움 SDK websockets>=15/Pandas>=3 요구는 같은 프로세스 환경에서 양립하지 않는다. SDK를 별도 자식 프로세스로 실행해 기존 수집기에 JSON 이벤트로 연결했다. 인증은 OS keyring에서 읽으며 추가 HTTP 서버는 만들지 않았다.

주 Torch 2.14.0+cu132와 일치하는 torchvision 0.29.1+cu132를 사용하고 불필요한 시스템 torchaudio 의존을 제거했다. FinRL-Trading은 원래 고정된 submodule을 직접 사용하며 중복 설치 배포판을 제거했다. 공식 원본과 학습 기본값은 수정하지 않았다. FinCast 실제 추론에서 누락됐던 beartype/einx/colt5-attention과 원본 도구의 tzlocal을 명세에 반영했다.

두 환경의 `pip check` 통과, 실제 CUDA 행렬 계산, FinRL/SB3 import, FinRL-Trading 데이터·평가 모듈 import, 키움 SDK import 검사를 확인했다. 기존 환경은 사용자 지시에 따라 `휴지통/.venv-previous-20261012-232811/`로 이동했다. 설치 스크립트는 lock 제약을 적용하고 설치를 이름만으로 건너뛰지 않는다.

### F6. 통합 요청 종료 시간이 없음 — 수정·자동검증 통과

일반 요청에 AbortController 60초, 대형 Expert 스냅샷을 저장하는 Champion 생성에 30분 제한을 적용했다. 정체된 요청 종료와 다음 요청 복구, 비 JSON HTTP 500 상태, JSON 오류 이유와 GET 계약을 전송 회귀 4개로 검증했다. 실제 Champion 생성은 약 6.4초에 완료했다.

### F7. CI 범위와 운영 버전 불일치 — 수정·로컬 검증 통과

CI Python을 3.13으로 맞추고 실제 FastAPI 전송 검사와 Node 22의 React 타입·운영 빌드·전송 회귀를 추가했다. 최소 CI는 GPU/모델 가중치/외부 인증을 설치하거나 실행하지 않는다. 로컬 실제 학습과 브라우저 실행은 별도 결과로 기록한다.

### F8. 모든 화면에 모듈 오류 노출 — 수정·브라우저 검증 통과

현재 큰 메뉴의 오류를 표시하고 다른 구역 오류 수와 진단 링크를 유지한다. 공통 진단은 모든 오류를 표시하고 통합 API 연결 실패는 전역 표시한다. Champion 오류를 주입한 자동 브라우저 검사에서 시장 화면·프로젝트 확장·공통 진단의 표시를 검증했다.

### F9. 평가 진입점에서 Expert 이력 삭제 — 수정·회귀 검사

실제 백테스트가 평가 첫 관측에서 Expert 최소 32일 이력 부족으로 실패했다. `official_cli`가 평가 기간 이전 행을 먼저 잘라내던 처리를 제거했다. 공식 환경은 기존 rolling 평가 기간만 거래하고 Expert는 관측 시점 이하의 원본 이력을 사용하므로 미래 입력은 사용하지 않는다. 진입점에서 전체 이력을 유지하는 회귀 검사를 추가했다.

### F10. 원본 주식 Expert의 최근 부분 일봉 선택 — 수정·회귀 검사

평가 마지막 관측에서 CRWD·META·T의 이전 일봉이 아직 저장되지 않아 최근 날짜의 17종목 입력이 불완전했다. 입력 준비에서 전체 원본 학습 종목이 모두 존재하는 가장 최근 과거 거래일을 선택하도록 수정했다. 미래 일봉·종목별 서로 다른 날짜·만든 가격은 사용하지 않는다. 완전한 과거 거래일이 없으면 오류를 유지한다. 공통 완료 거래일 선택과 누락 시 차단을 회귀 검사했다.

### F11. 공식 환경 종료 응답의 마지막 날짜 중복 — 수정·회귀 검사

PortfolioOptimizationEnv는 마지막 날짜에 도달한 다음 step에서 같은 상태·날짜를 반환하고 종료한다. 연결 코드가 종료 응답까지 다시 기록해 StrategyResult 평가의 날짜 재색인이 실패했다. 종료 응답의 가중치를 재기록하지 않도록 수정했고 실제 계약을 모사한 종료 회귀를 통과했다. 공식 환경·BacktestEngine 원본은 수정하지 않았다.

## 5. 실행 확인 결과

| 확인 | 결과와 의미 |
| --- | --- |
| Python 정합성·FastAPI 전송 | 23개 회귀 검사. JSON 숫자·삭제 캐시·SDK 이벤트·가격/계좌 계약·평가 이력 보존·실제 HTTP 전달 |
| React 타입·운영 빌드 | 통과 |
| 프론트 API 전송 | 4개 통과 |
| 실제 로컬 Chromium 화면 | 38개 등록 화면·시장 페이지 이동·오류 구역/진단 검사 2개 통과 |
| 주 환경/SDK 환경 pip check | 둘 다 통과 |
| 실제 GPU | RTX 3070 CUDA 계산·SB3 import 및 선택 Expert 11개 전부 cuda:0 추론 확인 |
| 신규 모델·실제 학습 | SAC, USD, AAPL/MSFT, 선택 Expert 11개, 105단계·업데이트 5회 완료. 기본 5,000단계 변경 없음 |
| 신규 모델 백테스트 | 2025-10-10~2026-10-09, 251개 실제 거래일의 Expert/정책 추론·공식 평가·결과 저장 완료. 가치 251행 유한값·날짜 중복 없음 |
| 현재 운영 선택 | 요청 범위를 넘긴 신규 정책 선택을 취소하고 작업 전 `champions/sac_champion_003/sac.zip` 선택으로 복원. 임의 생성한 004·007 및 생성·학습 폴더 004~007은 휴지통으로 폐기 |
| 앞선 실행 검증 | 신규 정책 선택 당시 system/check 10개 complete·38개 화면 검사 통과. 이후 선택 복원에 따라 현재 정책의 호환 상태와 구분 |

공식 원본 평가기는 가치·지표를 제공하고 가중치 이력/거래 표는 빈 DataFrame을 반환하므로 해당 파일·표가 비어 있을 수 있다. 가상 원장의 실제 체결 내역과 구분하며 기록을 만들어 채우지 않는다.

일반 API 상태 조회 성공을 전체 기능 성공으로 확대하지 않는다. 저장 모델은 원래 선택된 11개 Expert의 동결 스냅샷을 포함한다. 등록된 전체 65개 Expert 및 선택하지 않은 외부 모델 변환·다운로드를 모두 실행한 것은 아니다.

## 6. 보존·보안·실행 범위

- 모델·Replay·원장·인증·runtime·캐시·휴지통은 Git 제외 대상으로 보존했다. 이전 소스 변경도 백업 브랜치와 stash에 남아 있다.
- 실제 증권사 주문은 전송하지 않았다. 가상 원장의 다음 완료 바 체결은 독립 메모리 계좌 회귀로 검사한다.
- 키움 SDK의 실제 import와 수집기 이벤트 계약을 확인했으며 공급원별 원격 인증·모든 종목의 실시간 수신 성공은 보장하지 않는다.
- 공식 외부 프레임워크 전체 함수, 모든 등록 Expert, 수익성·수렴·거래 성과 개선은 검증 범위 밖이다.

## 7. 자동검증 재실행

설치: `scripts/install_windows.py`. 백엔드: 주 환경 Python의 `-m unittest discover -s tests`, `-m compileall -q backend scripts`. 프론트: `npm run typecheck`, `npm run build`, `npm run test:api`. 실제 로컬 서버가 실행 중일 때 `npm run test:browser`를 사용한다. 브라우저 스크린샷·trace와 실행 모델/백테스트 산출물은 Git 제외 runtime·test-results·외부 모델 폴더에 보존한다.

후속 GitHub 실행에서는 백엔드가 통과하고 Linux 프론트 빌드가 플랫폼별 Rollup 선택 의존성 누락으로 실패했습니다. 기존 패키지 버전을 유지하며 npm이 해석한 누락 플랫폼 패키지 기록을 lock에 반영하고 재검증했습니다.

## 미사용 설치 정리 — 2026-10-13

사용자의 폐기 지시에 따라 실행 참조·실행 중 프로세스·패키지 직접/간접 의존성을 확인했다. 주 환경 245개와 키움 환경 20개는 설치 명세의 의존성 그래프에 모두 연결돼 있어 유지했다. 프론트 기본 설치에서도 참조 없는 패키지는 없었으나 실제 Windows Node가 MSVC ABI를 사용함을 확인해 조건부 GNU 패키지를 분리했다.

이동한 상대 경로는 `.venv-previous-20261012-232811`, `runtime/verification/frontend-lock-install/node_modules`, `runtime/verification/frontend-lock-install-2/node_modules`, `frontend/node_modules/@rollup/rollup-win32-x64-gnu`이다. 모두 `휴지통/` 아래 동일 상대 경로로 이동했고 그 내부를 읽거나 삭제하지 않았다. 이동 후 양 환경 pip check·백엔드 회귀 23개·React 빌드·기존 서버 health를 확인했다. 새 모델·학습·Expert 실행은 수행하지 않았다.

사용자 지시에 따라 임의 생성한 `sac_champion_004.pt`, `sac_champion_007.pt`와 `runtime/official/champions/sac_champion_004`~`007` 폴더를 휴지통으로 이동했다. 기존 003 선택과 원본은 유지했다. 환경 불일치를 근거로 정책을 구형으로 단정하거나 신규 생성·학습을 임의 실행하지 않는다.

## 2026-10-13 메뉴 폐기 반영

사용자가 지정한 FinRL 메인의 9개 메뉴를 제거했다. 이전 절의 15개 기본 메뉴·38개 화면·FinRL ACTIONS/stock_workflow/평가 실행 설명과 해당 실행 검증은 제거 전 이력이다. 현재 기본 메뉴는 11개이며 FinRL 메인은 정책 학습과 모듈·도구만 제공한다. 전용 프론트 폴더 2곳, 백엔드 메뉴 연결 4개, finrl.operations, finrl_trading.backtest와 관련 API·CLI·결과 조회·타입·별칭을 제거했다. 전용 소스·컴파일 캐시는 휴지통으로 이동하고 기존 모델·계좌·가격·산출물은 보존했다. 새 정책 생성·학습·Expert 실행은 이 작업에 포함하지 않았다.

메뉴 폐기 후 실행 확인: 기본 메뉴 11개·등록 action 19개·실제 화면 29개. 제거한 backtest/preflight 및 8개 framework 요청은 모두 HTTP 404였다. Python 구문·TypeScript·운영 빌드·백엔드 21개·프론트 전송 4개·실제 브라우저 2개 검사에 통과했고 module_errors는 비어 있었다. 전용 예제 소스 캐시도 휴지통으로 이동했다.

## 2026-10-13 FinRL-Trading 보조 13개 메뉴 폐기

대상은 FMP 재무 데이터/뉴스, NASDAQ 100/S&P 500 조회, 가격/재무 CSV 전처리, ML 데이터 구성, TSMOM, Adaptive Rotation 개별 실행, 동일 비중, ML/산업별 ML 선택, 수익·성과 지표다. 각각 fundamentals, news, nasdaq100, sp500, process_prices, process_fundamentals, ml_dataset, tsmom, adaptive, equal_weight, ml, sector_ml, performance action에 대응한다.

공용 operations.py 안의 13개 등록·실행 분기와 전용 가격/종목 준비·CSV 처리 연결을 삭제했다. 원본 파일·컴파일 캐시는 휴지통으로 이동하고 남은 실행과 공급원 함수만 같은 경로에 유지했다. 프론트는 공용 동적 화면이므로 action 등록을 폐기하고 전용 필드·빈 전략/성과 구역을 제거했다. 독립 프론트 파일은 존재하지 않아 공용 화면 전체를 폐기하지 않았다.

이미지에 없는 adaptive_download/adaptive_single/adaptive_backtest/calendar/config_check 5개와 native_call, 공통 가격 조회·가격 수집·공급원 인증은 유지한다. 특히 가격 조회는 중앙 FinRL 학습/운영, csv_input은 native_call, 공식 Adaptive Rotation 소스는 남은 원형 실행에서 사용한다. 모델·데이터·계좌·인증은 변경하지 않았으며 새 정책 생성·학습·Expert 실행은 수행하지 않았다. 기존 기록의 19 action·29개 화면은 직전 폐기 단계의 이력이며 현재는 6 action·16개 화면이다.

실행 검증: menu_catalog와 framework 카탈로그가 동일한 6개 action(보조 5개+native_call)만 반환했다. 폐기한 13개 API는 전부 HTTP 404였으며 작업을 실행하지 않았다. 백엔드 회귀 22개·프론트 전송 4개·TypeScript·운영 빌드·실제 16개 화면 브라우저 2개 검사에 통과했고 module_errors는 비어 있었다. 서버 8766에 최신 소스를 적용했으며 외부 공급원 인증·실제 수집·남은 전략 실행의 성공을 이 결과로 확대하지 않는다.

## 2026-10-13 REA 등록·설치

사용자가 지정한 morluto/rea를 확인하고 공식 rea-agents 6.4.0 및 MCP Client 2.3.1을 backend/rea에 로컬 설치했다. 기존 Node 24.21.0을 사용하며 다른 Python/프론트 의존성·공식 정책·계좌·모델은 변경하지 않았다. REA 큰 메뉴와 분석·진단 화면, 단일 API의 상태/실행/원본 doctor/중지를 연결했다. 원본 MCP 세션을 유지해 대상·Evidence 문맥을 재사용하고 170개 도구의 원본 스키마/결과를 전달한다.

설치 검증용 최소 JavaScript 디렉터리 분석이 원본 MCP 도구로 성공했다. Windows에서 inspect_binary_layout은 원본 Linux x64 전용 pwntools 프로필 때문에 capability_unavailable을 반환했다. 원본 doctor도 Ghidra/Hopper와 에이전트 등록·스킬 등 미설정 항목을 보고했으며 이를 설치/실행 성공으로 확대하지 않는다. Codex 등 글로벌 에이전트 설정은 변경하지 않았고 임의 정책 생성·학습·Expert 실행을 하지 않았다.

REA 서버 적용 후 menu_catalog에 REA 큰 메뉴/분석·진단이 등록됐고 상태 API가 v6.4.0·Node 24.21.0·원본 도구 170개를 반환했다. rea/run을 통해 JavaScript 디렉터리 분석이 성공하고 inspect_analysis_view의 원본 source 스키마로 같은 Evidence를 후속 호출에서 재사용했다. 전체 17개 실제 화면·백엔드 24개·전송 4개·타입·빌드 검증이 통과했다. setup으로 글로벌 에이전트 등록을 변경하지 않았다.

## 2026-10-13 FinRL-Trading 큰 메뉴·남은 보조 화면 폐기

완료 대상: 보조 데이터·전략·도구, Adaptive Rotation 원형 데이터 준비·단일 실행·전체 백테스트, 시장 거래일, FinRL-X 설정 유효성. 큰 메뉴 등록·전용 workspace·FrameworkTools·5개 ACTIONS/execute·Rotation 설정 입력 참조·관련 링크·스타일·오류 이동 경로를 제거했다. 백엔드 메뉴 연결 2개, 프론트 전용 파일 2개, 컴파일 캐시 2개를 상대 경로를 유지해 휴지통으로 이동했다.

현재 5개 큰 메뉴·11개 화면이며 공통 실행 action은 native_call 하나다. 이전 절의 보조 5개 유지·17개 화면은 폐기 전 이력이다. operations.py에는 실제 가격 수집·연결 설정·공통 원본 호출에서 사용하는 공급원 인증 함수만 남겼다. data.py/finrlx 및 공식 FinRL-X 원본은 중앙 FinRL 가격·수집의 실제 의존성으로 유지한다. 모델·가격·계좌·인증·알고리즘 기본값은 변경하지 않았고 생성·학습·추론·전략 실행을 수행하지 않았다.

REA는 Codex 종속이 아니다. 기존 연결은 원본 CLI를 독립 Node 자식 프로세스로 실행한 MCP/stdio 방식이다. Codex 설정이나 로그인 없이 사용하며 원본 CLI의 scripts/rea.mjs --help 실행도 정상 종료했다. CLI 연결 방식을 새로 구현하거나 원본 REA를 변경하지 않았다. 심층 바이너리 엔진 미설정은 이전 보고와 같다.

실제 확인: 백엔드 24개·TypeScript·운영 빌드 통과. 서버 8766 적용 후 menu_catalog는 5개 구역·11개 화면·native_call 하나를 반환했고 module_errors는 비어 있었다. 삭제한 5개 실행 API는 모두 HTTP 404였다. API 전송 4개·실제 11개 화면 브라우저 2개 검사를 단일 프로세스로 순차 실행해 최종 6개 모두 통과했다. 최초 병렬 실행의 산출물 경로 충돌 및 재시작 중 연결 거부는 최종 순차 검증에서 해소했다. 실제 시세·학습·추론·가상체결·REA 심층 바이너리 분석의 성공을 이 결과로 주장하지 않는다.

## REA 목적별 실행·엔진 설정 메뉴

목적별 원본 도구 선택·바이너리 구조/세션/닫기·보관 Evidence 요약/페이지 조회 입력을 REA 메뉴에 연결했다. 엔진 경로는 단일 API와 configs/local/rea.json을 사용해 원본 자식 프로세스 환경에만 전달한다. 저장·진단·분석은 사용자 버튼 실행이며 자동 진단·자동 분석은 하지 않는다. 경로 존재·플랫폼 지원·원본 준비 확인·실제 분석 성공은 구분한다. Ghidra/JDK/Hopper 설치 자체와 실제 심층 분석 검증은 수행하지 않았다. 자동 검사는 사용자 직접 실행 대상으로 미실행이다. Windows 지원 근거: https://github.com/morluto/rea/blob/main/docs/windows-ghidra-p0.md .

프론트 빌드·서버 적용은 기존 start_server.py --apply-only --skip-checks로 완료했다. 자동 검사·브라우저 검증·엔진 doctor·실제 분석은 실행하지 않았다. 사용자는 기존 tests/test_state_integrity.py, tests/test_http_transport.py 및 frontend/package.json의 test:api/test:browser 스크립트로 직접 검사할 수 있다.

## REA Ghidra 설치·연결 완료

앞 절의 엔진 설치·실제 분석 미완료 상태를 해결했다. REA 6.4.0이 원본에서 검증한 Ghidra 12.1.4와 Temurin JDK 21.0.12.1+1 공식 ZIP의 SHA-256을 각각 공식 API의 값과 대조하고 설치했다. 한글 Java home 경로의 원본 판독 실패를 %LOCALAPPDATA%/stockrl-rea/engines의 영문 경로로 해결하고 기존 rea/settings로 연결했다. 전역 환경·Codex 설정·원본 라이브러리를 변경하지 않았다.

실제 확인: 원본 doctor --provider ghidra는 exit 0. 메뉴가 사용하는 단일 API로 설치된 실제 네이티브 PE javac.exe를 open_binary(provider_id=ghidra)로 열고 binary_overview 성공 후 close_binary로 소유 분석을 종료했다. 결과는 runtime/rea/ghidra-open-result.json 및 ghidra-overview-result.json, 준비 확인은 ghidra-readiness.json에 기록했다. CPU 작업인 설치·REA 분석 자식 프로세스를 두 코어·낮은 우선순위로 제한했다. 자동 검사 묶음·학습·정책 생성은 실행하지 않았다. Hopper는 Windows 원본 지원 범위 밖이며 Ghidra로 네이티브 분석을 제공한다.

완료 후 프론트 빌드·서버 적용을 수행했다. 재시작 때 소유 REA 세션은 정리하며 준비 확인 기록은 현재 엔진 경로와 일치할 때만 화면에 표시한다. 설치 ZIP·엔진·환경 경로는 로컬 저장 대상으로 Git에 포함하지 않는다.

## REA 파일 선택·실제 C 코드 복원

REA 작은 메뉴를 파일 복원·디컴파일로 변경했다. 메인 화면에서 파일을 선택하고 버튼 하나로 전체 함수의 C 형태 코드를 복원한다. 원본 batch_decompile을 사용하고 목록의 모든 함수 주소를 전달한다. 함수별 코드·검색·전체/개별 C 다운로드 및 서버 저장 경로를 제공하며 기존 JSON/엔진 도구는 고급 설정에 유지한다. 입력 복사본과 원본 열기 결과의 SHA-256을 대조하고 원본 파일은 실행·수정하지 않는다. 분석은 종료·오류 시 정리한다.

실제 실행: 선택 파일 업로드 → 복원 API로 javac.exe의 함수 126개를 처리했다. 코드 74개가 복원됐고 52개는 원본 도구가 복원 불가/오류로 반환했다. 61,316바이트 C 출력과 원본 Evidence를 runtime/rea/recovered/2c3639294e3b4ee8a72ab3791e31cab8에 저장했다. 원래 소스 프로젝트·원래 변수명/주석/빌드 구성 복원을 의미하지 않는다. 최초 연결에서 세션 열기의 result 응답과 분석의 Evidence 응답을 구분하지 못한 문제를 수정하고 실제 복원을 완료했다. 자동 검사 묶음은 실행하지 않았다. 원본 기능 근거: https://github.com/morluto/rea/blob/main/docs/native-investigation.md .

## REA 최종 범위: 분석·추출·실제 저장

최신 사용자 지시에 따라 재구현·실행·에이전트 연결 계획을 폐기했다. REA 역공학 큰 메뉴는 프로그램 분석과 프로젝트 탐색 두 작은 메뉴만 제공한다. 프로그램 분석에는 파일 선택·폴더 선택·웹사이트 분석 세 버튼이 있다. 기존 임의 도구/JSON/설정/진단 화면과 전용 공개 API를 제거하고 나머지 공식 실행·환경 코드는 실제 분석 의존성으로 유지한다.

백엔드: backend/rea/analysis/extract.py, artifacts.mjs, operations.py. 프론트: frontend/src/pages/rea/analysis/REAWorkspace.tsx. 저장: backend/rea_projects/<ID>/ (Git 제외). original은 추출 원문/원본 파일, inferred는 Ghidra 의사코드·REA 추론 관계, analysis는 관측 구조·함수·모듈·Evidence·한계다. README와 project.json을 함께 저장하며 사용자 버튼으로 Windows 저장 폴더를 연다. 별도 코딩 에이전트를 호출하거나 추출 프로그램을 재구현/실행하지 않는다. 웹 관측용 브라우저는 별도 프로필을 사용하고 분석 후 종료한다.

실행 결과: 공식 ASAR 파일 및 소스 폴더 입력에서 3개 원문 파일을 실제 저장하고 입력과 app.js 바이트가 같음을 확인했다. 관측 모듈/함수 JSON 폴더와 inferred/relationships.json도 실제 생성했다. 웹 입력에서는 테스트 페이지의 HTML·원본 JavaScript·내보내기 manifest와 웹 구조·추론 자료를 저장했다. 초기 브라우저 연결 파일의 Windows 공유 충돌은 준비 대기로 수정하고 성공했다. 저장 폴더 열기 API를 실제 호출해 Explorer에서 출력 경로를 열었다.

검사: 백엔드 26개, TypeScript, 운영 빌드, API·브라우저 7개 검사 통과. 실제 12개 화면과 REA 세 버튼·저장 원문 탐색을 확인했으며 JavaScript 오류/HTTP 500은 없었다. 폐기한 rea/run,doctor,settings,upload,recover 경로는 HTTP 404였다. 검사·빌드·분석은 두 CPU 코어·낮은 우선순위를 사용했다. 모델·정책·계좌·가격·알고리즘은 수정하지 않았고 새 학습·정책·재구현은 실행하지 않았다.

네이티브 입력 추가 실행: 실제 javac.exe를 프로그램 분석 API로 처리해 original/javac.exe 바이트 보존, inferred/decompiled.c 및 함수별 C 파일, analysis/functions.json을 확인했다. 추론 파일 75개(전체 C 1개+함수 C 74개)를 backend/rea_projects/e1109954f2b34c41ac52139d10e44436에 실제 저장했다. 52개 외부 DLL 참조에는 이 바이너리 안의 함수 본문이 없어 원본 결과대로 기록했다. 이 결과는 네이티브 원본 프로젝트의 완벽한 복원을 뜻하지 않는다.


### 2026-10-13 시장 · 저장 데이터 폐기 및 모듈 상태 구분

- 완료: 거래 운영의 `markets` 메뉴와 전용 프론트 폴더, 백엔드 `market_data_menu.py`, 해당 `.pyc`를 프로젝트 루트 `휴지통/`으로 상대 경로를 유지해 이동했습니다. 휴지통 내부는 열람하지 않았습니다.
- 완료: 단일 `/api`의 `collect` 등록·요청 모델·수집 작업 분기 및 시장 화면 전용 `prices` 상태 조회·`price_history` 함수를 제거했습니다. 학습 사전 확인·중앙 운영에서 사용하는 `database()`·가격 저장소·공통 데이터 모듈은 참조가 있어 유지합니다. 데이터·모델·설정은 변경하지 않았습니다.
- 코드 참조 조사: 웹 API·공식 CLI·작업 worker·키움 worker 진입점에서 이어지는 import와 프로세스 실행 경로를 확인했습니다. `expert_backends.py`는 `moe_native.py`, `expert_registry.py`는 `expert_backends.py`가 사용합니다. `scripts/`의 두 파일은 설치·서버 실행 CMD 및 서버 적용에서 사용됩니다. 남은 프로젝트 Python 비패키지 파일에서 추가 미참조 폐기 대상은 확인되지 않았습니다. 이는 코드 참조 조사이며 모든 기능 실행 검증을 의미하지 않습니다.
- 완료: 프로젝트 모듈을 전부 연결됨으로 표시하던 처리를 제거했습니다. 실제 진입점에서 이어지는 소스 참조, import 완료, 함수 실행 성공 기록을 구분합니다. 공통 실행 API로 호출 가능하지만 운영 코드 참조가 없는 공식 함수는 `호출 가능·사용 미확인`으로 표시합니다. `node_modules`·캐시·빌드 파일은 프로젝트 소스 목록에서 제외합니다.
- 완료: 상태·사유도 텍스트 검색에 포함하고 `실행 미확인`·`참조 없음` 필터를 추가했습니다. 실행 미확인만으로 미사용·폐기 대상으로 판정하지 않습니다.
- 검사 미실행: AGENTS.md의 사용자 직접 검사 지침에 따라 이번 변경의 테스트·타입 검사·브라우저 검증은 실행하지 않았습니다. 기존 브라우저 스크립트는 메뉴 11개와 markets 폐기를 반영했습니다. 사용자가 실행할 명령: `.venv\Scripts\python.exe -m unittest discover -s tests`, 프론트 폴더에서 `npm run typecheck`, `npm run test:api`, `npm run test:browser`.
- 빌드·서버 적용 결과와 커밋 상태는 아래 완료 기록에 별도 기재합니다.

- 완료 기록: 프로젝트 Python 소스 79개 참조 조사에서 미참조 비패키지 파일은 없었습니다. 전용 프론트 소스 3개, 백엔드 메뉴 1개, 해당 Python 캐시 1개, 기존 MarketScanner 빌드 파일 1개를 휴지통으로 이동했습니다. Vite 빌드 성공(3.98초). 기존 런처 `--apply-only --skip-build --skip-checks`로 React·백엔드 적용 완료. 실제 화면 동작·시장 수집·학습·추론·가상체결은 이번 변경에서 검사하지 않았습니다. 승인 범위 변경만 1회 커밋·push합니다.


### 2026-10-13 프로젝트 플랫폼의 대메뉴·작은 메뉴 구조 적용

- 대메뉴 5개: trading(거래 운영), finrl(FinRL 메인), rea(REA 역공학), extensions(프로젝트 확장), management(연결·관리). 각 대메뉴 아래 작은 메뉴 11개를 백엔드와 프론트에 동일하게 배치했습니다. 각 작은 메뉴 및 대메뉴 README는 역할·핵심 파일·import 진입점과 실행 미확인 상태를 설명합니다.
- 백엔드 연결: 작은 메뉴의 menu.py·handlers.py → 대메뉴 취합 파일 → menu_registry.py → web_api.py → 단일 /api. 기존 API 함수·요청 계약을 소속 메뉴로 이식했고 web_api.py는 1,026줄에서 12줄로 줄였습니다. 공유 HTTP 객체는 api_context.py, 전송·React 제공은 api_transport.py가 담당합니다.
- 프론트 연결: pages/대메뉴/작은메뉴/컴포넌트 → 대메뉴 취합 파일 → shell/menu_groups/menu_registry.ts. 메뉴·해시·기능을 유지했고 공통 화면 부품은 pages/shared/frameworks/에 모았습니다. 화면 공통 이름은 프로젝트 플랫폼입니다.
- REA 분석 구현은 rea/analysis/, 저장 프로젝트 탐색은 rea/project_browser/로 분리했습니다. 기존 원본 REA 설치 의존성과 CLI/MCP 연결을 사용합니다. 저장 결과 폴더 6개를 분석 대상 이름+생성 시각으로 실제 이동했습니다. 내부 ID는 유지했고 project.json의 물리적 경로와 분석 JSON의 경로 참조만 갱신했습니다. original/ 코드·바이너리 내용은 수정하지 않았습니다. 새 결과도 대상 이름+시각으로 저장합니다.
- 여러 메뉴가 함께 사용하는 상태·모델 실행 기반과 저장 정책의 클래스 import 경로는 유지했습니다. 모델·설정·계좌·가격 데이터·공식 FinRL·SB3 소스·알고리즘 기본값은 바꾸지 않았습니다. 자동 에이전트 호출·정책 생성·학습·프로그램 재구현은 실행하지 않았습니다.
- 기존 검사 스크립트의 import는 새 경로를 반영했습니다. 이번 작업의 테스트·타입 검사·브라우저 검증은 AGENTS.md에 따라 미실행입니다. 사용자 실행: `.venv\Scripts\python.exe -m unittest discover -s tests`, frontend에서 `npm run typecheck`, `npm run test:api`, `npm run test:browser`.
- 실제 결과: Vite 빌드 성공(4.62초). 서버 적용 및 커밋 결과는 다음 완료 기록에 별도 기재합니다.

- 사용자 추가 지침 반영: API→전체 메뉴 매니저→대메뉴별 소메뉴 매니저→기능의 계층을 AGENTS.md에 명시했습니다. 구조 경로는 영문 ASCII, 화면·README 설명은 한글을 허용합니다. REA 결과 폴더도 ASCII 대상명+시각으로 만들며 원본 이름은 메타데이터에 보존합니다. React·백엔드 적용 완료(검증 생략).

- 최종 구조 보정: 백엔드·프론트 대메뉴마다 submenu_manager를 분리해 하위 기능→소메뉴 매니저→대메뉴 등록→전체 메뉴 매니저→API 계층을 적용했습니다. 범용 플랫폼·REA 독립 소유권·새 기능 추가 시 중앙 API 및 금융 코드 수정 금지를 AGENTS.md에 명시했습니다.

- 완료 기록: 최종 메뉴 계층의 Vite 빌드 성공(5.50초), React·백엔드 적용 완료. 자동검증·타입 검사·브라우저 검증은 미실행입니다. 승인된 구조 이식 및 지침만 1회 커밋·push합니다.


### 2026-10-13 REA와 금융 프로젝트의 물리적 분리

- backend/stockrl/의 금융 폴더 배치는 유지했습니다. REA 전체 폴더(원본 설치 의존성 포함)는 backend/rea/로 실제 이동했습니다. 분석 결과 backend/rea_projects/는 이동·수정하지 않았습니다.
- API·전체 총괄·공통 HTTP 파일 4개를 backend/ 루트로 이동했습니다: web_api.py, menu_registry.py, api_context.py, api_transport.py. 총괄은 금융 대메뉴들과 독립 REA 대메뉴를 import합니다.
- 실행 진입점은 web_api:app입니다. 서버 소유권 확인·설치 스크립트·메뉴 import·프론트 오류 구역·검사 스크립트의 경로를 함께 갱신했습니다. 기존 금융 정책·계좌·가격·설정·알고리즘 기본값은 변경하지 않았습니다.
- 금융 운영에서 분리 이전 web_api의 요청 모델·함수를 찾던 참조는 실제 정책 학습/진단 모듈을 직접 import하도록 수정했습니다. REA 중지의 불필요한 금융 진단 import를 없애고 REA 종료 처리는 해당 프로젝트의 라우터 종료 콜백으로 이동했습니다. 정책 생성·학습·모델 실행은 수행하지 않았습니다.
- 모듈 목록은 새 물리적 위치를 반영해 StockRL·REA·Platform 소스를 구분합니다. 연결·import·실행 미확인은 기존 의미를 유지합니다.
- 사용자 직접 검사 지침에 따라 테스트·타입·브라우저 검증은 실행하지 않습니다. 실행할 기존 스크립트: .venv\Scripts\python.exe -m unittest discover -s tests; frontend에서 npm run typecheck, npm run test:api, npm run test:browser. 빌드·서버 적용 결과는 아래 완료 기록에 기재합니다.

- 완료 기록: REA 폴더 및 공통 파일 4개 물리적 이동 완료. 옛 StockRL 위치의 공통 파일 Python 캐시 4개는 상대 경로를 유지해 휴지통으로 이동했습니다. 프론트 빌드 성공(5.43초), 새 web_api:app으로 React·백엔드 적용 완료. 테스트·타입·브라우저 검사 미실행. 승인된 이동과 필수 참조 수정만 1회 커밋·push합니다.


### 2026-10-13 금융 대메뉴 통합

- 전체 대메뉴는 금융(finance)과 REA(rea) 두 개로 등록합니다. 기존 거래 운영·FinRL·프로젝트 확장·연결 관리의 금융 화면 9개는 금융 내부 소메뉴입니다. REA 화면 2개는 독립 대메뉴로 유지합니다.
- 백엔드: stockrl/submenu_manager.py가 금융 내부 기능 분류의 소메뉴와 라우터를 취합하고 stockrl/finance_menu_manager.py가 금융 대메뉴를 등록합니다. backend/menu_registry.py는 금융과 REA 매니저만 import합니다. API 작업명·메뉴 해시·기능·모델·데이터·설정·알고리즘 기본값은 변경하지 않았습니다.
- 프론트: trading·finrl·extensions·management 폴더를 pages/finance/로 실제 이동하고 import·백엔드 화면 경로·README를 갱신했습니다. 예전 독립 대메뉴 등록 파일 8개 및 해당 Python 캐시를 의존성 확인 후 휴지통으로 이동했습니다. 금융 대메뉴 내부 오류는 관련 화면별 표시를 유지합니다.
- 기존 검사 스크립트는 대메뉴 두 개를 반영했습니다. 사용자 직접 검사 지침에 따라 테스트·타입·브라우저 검증은 미실행입니다. 사용자가 실행할 명령: .venv\Scripts\python.exe -m unittest discover -s tests; frontend에서 npm run typecheck, npm run test:api, npm run test:browser.

- 완료 기록: 금융 폴더 4개 이동, 옛 대메뉴 등록 파일 8개·캐시 4개 휴지통 이동. Vite 빌드 성공(5.21초), React·백엔드 적용 완료. 이번 변경의 테스트·타입·브라우저 검증 미실행. AGENTS.md의 기존 로컬 변경은 유지하고 이번 코드 커밋에는 포함하지 않습니다.


### 2026-10-13 루트 폴더 정리

- 긴 루트 문서는 docs/history.md, 설정 문서는 docs/settings.md, 검토 보고서는 docs/project_review.md로 실제 이동했습니다. 루트 README는 짧은 현재 구조 안내로 교체했고 문서 링크를 조정했습니다.
- requirements/를 scripts/requirements/로 이동해 설치·CI 경로를 맞췄습니다. 설치 명세의 버전·내용은 바꾸지 않았습니다.
- 공식 FinRL-X 서브모듈은 vendor/FinRL-X/로 Git 이동했습니다. 원본 소스·알고리즘·커밋은 유지하며 import·설치 경로만 변경했습니다.
- src/·logs/·results/는 내용이 없는 폴더임을 확인하고 휴지통 이동을 시도했습니다. 경로 충돌이 있으면 해당 빈 폴더의 이동을 보류합니다.
- configs/·data/·runtime/·기존 가상환경·금융 모델과 REA 저장 결과는 이동하거나 변경하지 않았습니다. 새 backend/ 루트 API 및 독립 REA Python 소스도 적용 대상에 포함하도록 기존 런처 소스 분류를 조정했습니다.
- 테스트·타입·브라우저 검증은 사용자 직접 실행 지침대로 미실행입니다. 프론트 소스 변경이 없어 새 프론트 빌드는 실행하지 않습니다. 적용·커밋 결과는 아래 기재합니다.

- 실제 결과: 빈 logs/·results/는 휴지통 이동 완료, 빈 src/는 휴지통 경로 충돌로 보류했습니다. 공식 서브모듈 커밋은 4409abe925c904e570be78ebfb5e77ac3491dff8로 유지됐고 서브모듈 소스 변경은 없습니다. 첫 적용에서 런처의 git -C FinRL-X 참조가 실패해 vendor/FinRL-X로 수정한 뒤 서버 적용 완료했습니다. 테스트·타입·브라우저 검증·새 프론트 빌드는 미실행입니다. 기존 AGENTS.md 로컬 변경은 커밋에서 제외합니다.


### 2026-10-13 REA 저장 결과의 소메뉴 폴더 귀속

- rea/는 독립 REA 기능 코드이며 rea_projects/는 프로젝트 탐색 화면에 연결된 저장 결과였습니다. 저장 결과는 backend/rea/project_browser/saved_projects/로 실제 이동해 REA 소메뉴 아래에 귀속했습니다. 저장·목록·파일 탐색·폴더 열기는 같은 OUTPUT을 사용합니다.
- 기존 프로젝트 ID와 원본/추론 파일 내용은 유지하고 project.json의 물리적 폴더 및 분석 JSON의 생성 경로 참조만 갱신했습니다. 새 분석 결과도 같은 위치에 저장됩니다.
- Git 제외·설치 패키지 제외·모듈 목록 제외·런처 소스 적용 제외를 새 위치로 맞춰 추출한 코드가 실행 모듈이나 대메뉴로 등록되지 않도록 했습니다. README 및 기존 경로 보호/재귀 복사 검사 스크립트도 새 경로를 반영했습니다.
- 테스트·타입·브라우저 검사는 사용자 직접 실행 지침대로 미실행입니다. 사용자 실행 명령은 scripts/README.md에 있습니다. 새 정책·학습·코딩 에이전트·추출 프로그램 실행은 수행하지 않았습니다.

- 실제 결과: 저장 프로젝트 6개 이동 완료. 생성 분석 JSON의 경로 참조 3개 파일 및 필요한 경로 키를 갱신했습니다. 서버 적용 완료(검증 생략). 프론트 기능·해시·API 작업명은 유지하며 원본/추론 파일은 변경하지 않았습니다. 이번 작업의 테스트·타입·브라우저 검증은 미실행입니다.


### 2026-10-13 REA 메뉴 이름·폴더·주소 통일

- 백엔드와 프론트 폴더를 program_analysis/·project_explorer/로 실제 변경했습니다. 프론트 파일과 함수도 ProgramAnalysis·ProjectExplorer로 맞췄습니다. 메뉴 ID와 화면 주소는 rea/program_analysis·rea/project_explorer로 통일하고 링크·import·검사 스크립트·저장 경로·Git/패키지/적용 제외를 함께 갱신했습니다. 분석 결과 6개의 내부 ID와 원본/추론 내용은 유지하고 경로 메타데이터만 갱신했습니다.
- backend/continual_trading_agent.egg-info는 pip install -e . 과정의 setuptools 빌드 결과입니다. 실제 설치의 동일 이름·버전 dist-info가 .venv/Lib/site-packages/에 있으며 editable .pth는 backend/ 코드 경로를 참조합니다. backend/의 중복 빌드 메타데이터는 휴지통으로 이동했고 README에 이유·위치를 기록했습니다. 재설치 시 빌드 결과가 다시 생성될 수 있습니다. 설치된 dist-info와 .pth는 변경하지 않았습니다.
- 테스트·타입·브라우저 검증은 사용자 직접 실행 지침에 따라 미실행입니다. 기존 AGENTS.md 로컬 변경은 유지합니다.

- 완료 결과: 메뉴 폴더·파일·ID·화면 주소·저장 경로 이식 완료, 중복 egg-info 휴지통 이동 완료. 프론트 빌드 성공(5.63초), React·백엔드 적용 완료. 테스트·타입·브라우저 검사 미실행.
