# Continual Trading Agent

TradingMoE를 중심으로 금융 시계열 전문가를 실행하고, 가상계좌의 체결 결과로 정책을 업데이트하는 로컬 운영 도구입니다. Python이 API와 실행 관리를 맡고, React 화면은 Python 서버가 정적 파일로 제공합니다.

## 현재 동작 구조

- 시장 Feed, Champion, Candidate, 전용 TradingMoE 실행은 각각 제어됩니다. 서버를 켜는 것만으로 모델이나 Feed를 시작하지 않습니다.
- Champion은 고정된 운영 정책이고 Candidate와 전용 TradingMoE는 온라인 학습 정책입니다. 각 실행은 독립된 가상계좌와 상태를 사용하며, 이 분리는 `stable_champion` 설정으로 제어됩니다. Candidate 등록은 `MoE 생성`에서 만든 TradingMoE 구성을 `candidate.pt`로 교체하는 방식으로 진행합니다. 승급은 실제 학습 가중치를 고정해 비교하고, 통과한 Adapter·Router·Fusion·Attention·Controller와 optimizer를 Champion에 적용합니다. 이전 Champion 학습 상태는 `모델/rollback`에 보존합니다.
- TradingMoE는 선택된 시장 분석 전문가와 매매 판단 전문가를 Router·Fusion·Attention·Controller로 연결합니다. 원본 전문가 가중치는 고정하고, 확정된 가상계좌 손익으로 Adapter·Controller를 학습합니다. CPU 학습은 추론과 분리되며 TorchRL의 정책 손실을 사용합니다. 행동 당시 확률·정책 버전을 기록하고, 확률 없는 이전 경험은 value 학습으로 처리합니다.
- 가상 주문은 체결 비용과 계좌 손익을 반영합니다. 현재 서버 상태에서 실제 주문 실행은 비활성화되어 있습니다.
- 운영의 live 모드는 수집기의 완료 시세를 Expert 입력으로 사용합니다. 주식 정책에는 완료 일봉과 실제 가상계좌 상태를 공급하며, 입력 부족은 전문가별 상태로 표시합니다. MacroHFT의 native 36+9 특징과 MarketGPT의 ITCH 입력은 해당 실시간 원본 스트림이 있을 때만 사용합니다. 과거 ETHUSDT 입력은 명시적인 historical 모드에서 사용합니다.

화면은 `운영`에서 전체 실행 상태·계좌·학습·자원을 확인하고, `자동매매`에서 Champion·Candidate·TradingMoE의 실행 제어와 가상계좌를 확인하도록 나뉩니다. `MoE 생성`에서는 시장 분석 Expert와 매매 판단 Expert를 선택해 독립 TradingMoE 파일을 만들고 Candidate로 등록합니다. `승급전`은 등록된 Candidate와 Champion의 평가를 담당합니다.

## Windows 설치 및 실행

새 PC 설치 절차는 [Windows 설치 안내](docs/windows-install.md)를 따릅니다. `설치.cmd`는 Python 3.13을 사용하고 전문가 실행 환경을 준비합니다. CUDA 의존성 설치에 많은 디스크 공간과 시간이 필요할 수 있습니다. NVIDIA GPU 사용에는 호환되는 드라이버가 필요합니다. 통합 실행 파일은 Node.js LTS와 프론트엔드 의존성 설치도 필요로 합니다.

1. 저장소를 clone하거나 GitHub에서 내려받습니다.
2. Node.js LTS를 설치한 뒤 `설치.cmd`를 실행합니다.
3. `frontend` 폴더에서 `npm ci`를 한 번 실행합니다.
4. 모델을 실행하려면 기존 PC의 바탕화면 `모델` 폴더를 새 PC 바탕화면으로 복사하거나 필요한 Expert 가중치를 다시 다운로드합니다. 체크포인트와 원본 전문가 가중치는 GitHub에 포함되지 않습니다.
5. `서버켜기.cmd`를 실행합니다. Python API `http://127.0.0.1:8766`과 React/Vite 화면 `http://127.0.0.1:5173`을 함께 켜고 브라우저를 엽니다.
6. 화면에서 Feed와 실행할 모델을 각각 시작합니다.

`프론트개발서버끄기.cmd`는 Vite만 종료하며 Python API 서버는 계속 실행합니다. 운영용 정적 화면은 Python 서버의 `http://127.0.0.1:8766`에서 제공됩니다.

## 개발

Python 패키지 메타데이터와 기본 의존성은 `pyproject.toml`, Windows 전문가 환경은 `requirements/moe.txt`와 `requirements/moe-toto.txt`에 정의되어 있습니다. 설치 스크립트는 전문가 의존성을 별도 환경으로 나눠 설치합니다.

```powershell
cd frontend
npm ci
npm run dev       # 개발 UI: http://127.0.0.1:5173, /api는 8766으로 전달
npm run typecheck
npm run build     # 결과: frontend/dist
```

Python 서버는 `frontend/dist`를 제공합니다. 프론트엔드를 수정한 뒤 운영 화면에 반영하려면 빌드를 다시 실행해야 합니다.

운영 학습 설정은 `configs/online_learning.json`에서 읽습니다. reward horizon, batch, optimizer step 수, learning rate, checkpoint 주기와 평가 조건이 이 파일에 정의되어 있으며 worker 상태의 `effective_settings`에서 실제 적용값을 확인할 수 있습니다. 기존 미성숙 reward에는 판단 당시 horizon을 유지합니다.

학습 checkpoint는 원본 Expert를 포함한 `<모델명>.pt`와 작은 `<모델명>.trainable.pt`로 구성됩니다. loader는 작은 파일이 있으면 함께 복원합니다. 다른 PC로 학습을 이어가려면 두 파일과 계좌·replay·evidence 상태를 함께 옮깁니다. checkpoint는 optimizer와 RNG도 복원합니다. 계좌·미성숙 결과는 같은 SQLite transaction으로 저장하고, JSON 표시 파일이 유실돼도 복구합니다. 실행 실패는 제한된 횟수와 backoff로 복원하며, 명시적으로 정지한 모델은 재시작하지 않습니다. 승급 평가 전 Champion·Candidate를 저장 후 정지하고, 저장 이후 새로 수집한 실시간 구간의 동일 조건 평가를 통과하면 `학습 가중치 승격`을 실행합니다. `이전 Champion 복원`은 가중치와 optimizer를 복원하며 운영계좌를 초기화하지 않습니다.

과거 데이터 실행은 별도 상태 폴더를 지정합니다.

```powershell
& artifacts/experts/venv/Scripts/python.exe scripts/run_native_vertical_trading.py --root artifacts/experts --checkpoint "$env:USERPROFILE/Desktop/모델/TradingMoE.pt" --state runtime/trading_moe/historical --mode historical --resume --steps 6
```

계좌와 학습 상태는 각 PC의 로컬 저장소에 남고 GitHub에는 올라가지 않습니다. 다른 PC에서 계좌와 학습을 이어가려면 모델을 정상 정지한 뒤 실행 상태 자료를 별도로 옮겨야 합니다. 저장 위치와 이동 범위는 [저장 위치 안내](docs/project-storage.md)를 참고하세요. 비밀번호·API 키를 저장소에 넣지 마십시오.

## 문서

- [문서 안내](docs/README.md)
- [Champion/Candidate 실행 제어](docs/model-lifecycle.md)
- [TradingMoE 학습·가상매매](docs/trading-moe-learning.md)
- [MoE 생성과 후보 평가](docs/assembly.md)
- [전문가와 모델 파일 배치](docs/project-storage.md)
- [주식 정책 전문가](docs/stock_policy_experts.md)
- `docs/reports/`의 수치와 측정 결과는 해당 기록 시점의 자료입니다. 현재 실행 상태나 계좌 값은 로컬 대시보드/API에서 확인합니다.
