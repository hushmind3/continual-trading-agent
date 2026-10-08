# FinRL-X MoE Operations

실시간 시장 데이터와 기존 `champion.pt` MoE를 연결하는 금융 운영 도구입니다. FinRL-X의 목표 비중 중심 구조를 기준으로 데이터·전략·위험검사·가상계좌를 연결하고, TorchRL PPO가 실제 시장 결과로 의사결정부를 학습합니다.

## 동작

`실시간 시세 → 사용 가능한 frozen Expert 출력 → 학습된 MoE 결합부 / 64D latent → 시장·계좌 feature → TorchRL Allocator → target weights → 잔고·가격 유효성 확인 → FinRL-X StrategyResult → 가상체결 → 비용 반영 손익 → 지속학습`

- Expert 원본 가중치는 frozen입니다. `champion.pt`의 실제 Adapter·Router·Fusion·Attention·Controller를 복원하며, 새 랜덤 정책으로 대체하지 않습니다.
- 종목 비중·현금 비중·비중 변경·손실 대응은 모델이 결정합니다. 고정 비중·turnover 제한이나 MDD 강제 청산 규칙을 적용하지 않습니다. 현금 계좌의 잔고, 체결 비용과 실제 가격은 그대로 계산합니다.
- Expert 실행, MoE 판단·계좌, CPU 학습은 별도 프로세스입니다. 큰 Expert는 순차적인 단기 작업 프로세스에서 실행하며 완료 후 모델 매핑과 임시 메모리를 해제합니다. 작은 정책은 CPU에서, 큰 예측모델은 설정과 측정된 자원에 맞는 장치에서 실행합니다.
- 큰 원본 PT를 매번 다시 쓰지 않고, 학습한 결합부·Allocator·optimizer 상태를 작은 정책 버전으로 저장합니다. 운영 판단에는 발행된 최신 버전이 반영됩니다.
- 가상체결은 다음 완료 시세에서 처리하며, 수수료·가격 미끄러짐·계좌 비용을 포함합니다. 원화와 달러 계좌는 별도로 계산합니다. 실제 주문은 연결하지 않습니다.
- 경험 처리와 계좌·미체결 상태는 SQLite transaction으로 함께 저장합니다. 정책 checksum, 버전 복원, 프로세스 식별과 재시도로 재시작을 지원합니다.
- MacroHFT 36+9, MarketGPT ITCH, DAPO sentiment/risk처럼 필수 원본 입력이 없는 Expert는 입력 필요 상태로 표시합니다. 과거 입력을 현재 데이터로 위장하지 않습니다.
- 원본 MoE에는 Expert 20개가 포함됩니다. 실제 실행은 선택한 Expert의 입력·RAM·VRAM 조건에 따라 달라지며, 자원이 부족하면 실행을 보류하고 화면에 자원 대기로 표시합니다.
- Expert 원본 가중치는 선택한 `champion.pt`에서만 읽습니다. 별도 Expert 가중치 파일 읽기는 차단하며, 패키지에서 모델이 누락됐으면 원본을 포함해 다시 패키징해야 합니다. 학습된 결합부·Allocator·optimizer는 작은 정책 버전으로 저장합니다. 시세·호가·뉴스 분석 값은 모델 가중치와 별개의 실시간 입력입니다.

## 실행

Windows에서는 Python 3.13, Node.js LTS, NVIDIA GPU에 맞는 드라이버를 준비한 뒤 `설치.cmd`를 실행합니다. 모델 파일은 바탕화면 `모델/champion.pt`를 사용하며 GitHub에 포함되지 않습니다.

`서버켜기.cmd`는 기본 프로젝트에서 Python API와 Vite를 함께 시작합니다.

- 운영 UI / API: <http://127.0.0.1:8766>
- 개발 UI: <http://127.0.0.1:5173>

시세·MoE·가상체결·자동학습은 화면에서 제어합니다. 키움 App Key와 Secret은 연결 화면에서 확인하며 운영체제 보안 저장소를 사용합니다. 국내 체결가와 미국 FE 시세는 공식 키움 SDK를 통해 수신합니다.

실행 여부, 시세 연결, 정책 버전, 학습 횟수와 계좌 수치는 운영 화면과 `/api/state`에서 확인합니다. 이 문서는 구조와 사용 방법을 설명하며 실시간 상태 수치를 보관하지 않습니다.

## 설정과 저장

- 운영 설정: `configs/operations.json`
- 원본 모델: `Desktop/모델/champion.pt`
- 계좌·경험·시세·프로세스 상태: `runtime/finrlx`
- 정책·optimizer 버전: `runtime/finrlx/policies`
- React / Tailwind CSS / Vite: `frontend`
- 운영 API·Expert 서비스·TorchRL 학습: `src/stockrl/platform`

`runtime`, `.venv`, `node_modules`, 키움 로컬 설정과 가중치는 Git에서 제외합니다. 다른 PC에서 이어서 운영하려면 정상 정지 후 원본 모델과 `runtime/finrlx`를 함께 옮깁니다.

## 개발 확인

```powershell
$env:PYTHONPATH="src"
$env:PYTHONUTF8="1"
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
cd frontend
npm run typecheck
npm test
npm run build
```

브라우저 테스트는 실행 중인 8766 서버와 설치된 Microsoft Edge를 사용합니다. 빌드 결과 `frontend/dist`를 Python 서버가 직접 제공하며 `no-store`로 응답합니다.

상세 구조는 [운영 architecture](docs/architecture.md), 설치는 [Windows 설치](docs/windows-install.md), 저장 위치는 [저장 안내](docs/project-storage.md)를 참고하세요.
