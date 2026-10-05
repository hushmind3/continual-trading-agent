# Continual Trading Agent

TradingMoE를 중심으로 금융 시계열 전문가를 실행하고, 가상계좌의 체결 결과로 정책을 업데이트하는 로컬 운영 도구입니다. Python이 API와 실행 관리를 맡고, React 화면은 Python 서버가 정적 파일로 제공합니다.

## 현재 동작 구조

- 시장 Feed, Champion, Candidate, 전용 TradingMoE 실행, 자동 조립 시험은 각각 제어됩니다. 서버를 켜는 것만으로 모델이나 Feed를 시작하지 않습니다.
- Champion과 Candidate는 독립된 실행 상태와 가상계좌·학습 상태를 유지합니다. 자동 조립은 Candidate 자리를 이용해 후보를 평가하며, 8GB 모델 파일을 후보마다 복제하지 않습니다.
- TradingMoE는 시장 분석 전문가, MacroHFT 정책 전문가, 주식 정책 전문가의 등록 정보를 이용해 현재 입력에 적용 가능한 의견을 모읍니다. 원본 전문가 가중치는 보존하고, 조합과 제어에 연결된 학습 가능한 부분을 업데이트합니다.
- 가상 주문은 체결 비용과 계좌 손익을 반영합니다. 현재 서버 상태에서 실제 주문 실행은 비활성화되어 있습니다.
- 전용 TradingMoE 연속 실행은 프로젝트에 포함된 MacroHFT 공식 ETHUSDT 과거 입력을 사용합니다. 이는 실시간 ETH 매매나 수익성 검증을 뜻하지 않습니다. 주식 정책은 필요한 종목·기간 입력이 있을 때만 적용됩니다.

## Windows 설치 및 실행

새 PC 설치 절차는 [Windows 설치 안내](docs/windows-install.md)를 따릅니다. `설치.cmd`는 Python 3.13을 사용하고 전문가 실행 환경을 준비합니다. CUDA 의존성 설치에 많은 디스크 공간과 시간이 필요할 수 있습니다. NVIDIA GPU 사용에는 호환되는 드라이버가 필요합니다.

1. 저장소를 clone하거나 GitHub에서 내려받습니다.
2. `설치.cmd`를 실행합니다.
3. 모델을 실행하려면 기존 PC의 바탕화면 `모델` 폴더를 새 PC 바탕화면으로 복사합니다. 체크포인트와 원본 전문가 가중치는 GitHub에 포함되지 않으므로, 이 파일 없이 받을 수 있는 것은 코드와 화면까지입니다.
4. `서버켜기.cmd`를 실행하고 브라우저에서 `http://127.0.0.1:8766`을 엽니다.
5. 화면에서 Feed와 실행할 모델을 각각 시작합니다.

일반 사용 때는 Python 서버만 필요합니다. Node/Vite는 프론트엔드 개발 및 빌드에만 사용합니다. 서버 실행과 브라우저 화면 제공에는 Vite 프로세스가 필요하지 않습니다.

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

## 파일과 상태 저장

| 위치 | 용도 | Git 포함 |
| --- | --- | --- |
| `src/stockrl/` | Python API, Feed, 전문가 등록·실행, 가상계좌, 학습, 평가 | 예 |
| `frontend/` | React 19, TypeScript, Tailwind CSS, Vite 화면과 빌드 | 소스와 Python 서버용 빌드 결과 포함 |
| `artifacts/experts/` | 전문가 원본 코드·설정·필요 입력자료와 설치 환경 | 추적 대상만 포함; 로컬 환경·제외 자료는 미포함 |
| `Desktop/모델/` | TradingMoE 및 운영·전문가 체크포인트 | 아니요 |
| `configs/` | 기본값과 운영 설정. 컴퓨터별 설정·자격 증명은 로컬에서 관리 | 기본 파일만 |
| `runtime/` | 계좌, 미학습 경험, 가상매매·Feed 진행 상태, 자동 조립 상태, 로그 | 아니요 |

프로젝트 기본 실행 상태는 `runtime/markets/korea`에 저장됩니다. TradingMoE와 자동 조립의 추가 상태도 `runtime/` 아래에 저장됩니다. 새 컴퓨터에서 계좌와 학습을 이어가려면 모델을 정상 정지하고 필요한 `runtime/` 자료를 별도로 옮겨야 합니다. 비밀번호·API 키를 저장소에 넣지 마십시오.

## 문서

- [문서 안내](docs/README.md)
- [Champion/Candidate 실행 제어](docs/model-lifecycle.md)
- [TradingMoE 학습·가상매매](docs/trading-moe-learning.md)
- [자동 조립과 후보 평가](docs/assembly.md)
- [전문가와 모델 파일 배치](docs/project-storage.md)
- [주식 정책 전문가](docs/stock_policy_experts.md)
- `docs/reports/`의 수치와 측정 결과는 해당 기록 시점의 자료입니다. 현재 실행 상태나 계좌 값은 로컬 대시보드/API에서 확인합니다.
