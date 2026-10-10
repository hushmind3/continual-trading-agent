# React 프론트 복원 · SAC 연결

디자인 기준: Git 커밋 `f1539571604f23a05f47761b25fc0448d1a12db5`의 흰색 테마, 상단 7개 메뉴, 카드·Drawer·탭·공통 버튼.
현재 main의 `framework.py`, FinRL-X 서브모듈, FinRL, SB3 학습 구현은 유지합니다.

## 화면·API 연결

| 화면 | 실제 API | 연결 대상 |
| --- | --- | --- |
| 운영 | GET state | SAC 저장 메타데이터, ResourceMonitor, 데이터·작업 현황 |
| MoE | GET state, POST experts/register, POST experts/select | ExpertRegistry 등록·선택·동일 모델 버전 교체·해제, 입력 계약, 실제 status.json 추론·자원 기록 |
| 시장 | GET state, GET prices, GET connections, POST collect | DataStore 가격 조회, 종목 선택, 공식 FMP fetch_price_data 수집 |
| 계좌 | POST preflight/backtest, POST backtest, GET result/weights 및 result/trades | 원본 BacktestEngine 가치·지표·가중치·거래 내역 |
| 학습 | POST preflight/train, POST train, POST stop, GET checkpoint | 공식 SAC 새 학습·이어 학습·중지, Replay/Actor/Critic/기본값, 로그, 실제 저장 파일 |
| 연결 | GET connections, GET state | 로컬 API, 공식 FMP 인증 설정 유무, 키움/Alpaca 미연결 여부 |
| 진단 | GET state, GET logs, GET modules | 실제 프로세스·CPU/RAM/VRAM/I/O, 라이브러리 버전·로그·소스 모듈 |

API는 FastAPI로 기존 함수·모듈을 호출하는 연결 계층입니다. 학습 알고리즘·Loss·Replay·환경·공식 기본값은 변경하지 않습니다.

## 기능 상태

현재 정책은 ExpertObservation wrapper의 8개 요약 관측을 SAC에 전달합니다. 이전 Champion/PPO 전용 controls·library·rollback API는 호출하지 않습니다.

과거 두 통화 가상계좌·키움 인증/실시간 시세/주문·자동 양자화 작업·Expert 검색·버전 rollback·웹 설정 편집은 현재 실행 경로에 없습니다. 원래 메뉴와 관련 기능 영역을 유지하면서 미연결/제거 상태와 사유를 표시하고 실행을 막습니다.

수치 출처: 라이브러리 설치 버전/기본값, 현재 train_sac 예제, SB3의 저장 파일·load_from_pkl, 원본 stdout 로그, 실제 DB·BacktestResult 파일, Expert status.json. 미저장/미측정 수치는 가정해서 채우지 않습니다.

## 개발 및 검증

운영: 루트의 `서버켜기.cmd` → 127.0.0.1:8766. 설치된 TypeScript·Vite로 검사·빌드한 뒤 FastAPI 하나에서 React 정적 파일과 현재 SAC API를 제공합니다. 재실행은 소유권을 확인하고 기존 서버를 재사용합니다.
개발: `npm run dev` → 127.0.0.1:5173. `/api`는 8766 통합 서버로 전달됩니다. 개발 서버는 통합 런처에서 자동 실행하지 않습니다.
`npm run typecheck`, `npm run build`, `npm test`.

화면 테스트는 실제 로컬 API를 조회합니다. 학습 시작 POST는 요청 본문 검증 시에만 가로채며, 실제 장시간 학습·가격 수집·모델 변경은 테스트에서 실행하지 않습니다. 오류 경로는 실제 API를 호출합니다.
화면 테스트 기본 주소는 8766입니다. 개발 주소로 별도 검증할 때는 `FRONTEND_TEST_URL=http://127.0.0.1:5173`을 사용합니다.
설치된 Playwright 브라우저 경로를 지정하려면 `PLAYWRIGHT_CHROMIUM_EXECUTABLE`을 사용할 수 있습니다. 현재 테스트는 운영 정적 파일과 개발 proxy가 같은 백엔드 PID를 사용하는지도 확인합니다.

복원 전 프론트는 `runtime/frontend-before-f153957-*`에 보관했습니다. 현재 backend나 Git HEAD를 과거 커밋으로 되돌리지 않았습니다.
