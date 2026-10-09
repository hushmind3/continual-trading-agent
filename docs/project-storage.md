# 저장 위치

| 경로 | 역할 |
| --- | --- |
| `.venv` | 하나의 운영 Python 환경 |
| `frontend/src` | React 화면·작은 UI 부품·API 연결 |
| `frontend/dist` | Python 서버가 제공하는 최신 빌드 |
| `configs/operations.json` | 학습·위험·자원·모델·입력 설정 |
| `configs/local/provider_settings.json` | 키움 환경과 공개 연결 상태 |
| Windows 자격 증명 저장소 | App Key·Secret |
| `Desktop/모델/champion.pt` | 선택된 Expert 실제 가중치·슬롯 정의·정상 정지 시 최신 중앙 학습 상태 |
| `Desktop/모델/expert-packages` | 불변 frozen Expert 가중치·원본 정의·입력 계약 |
| `runtime/finrlx/operations.sqlite3` | 통화별 계좌·체결 원장·미체결·경험·처리 여부·이벤트 |
| `runtime/finrlx/policies` | 학습 상태·optimizer·슬롯 선택·학습 세대·checksum·복원 버전 |
| `runtime/finrlx/expert-library.json` | 패키지 목록·실제 추론 검사·현재 사용 슬롯 |
| `runtime/finrlx/live` | 실시간 tick·완료 분봉·일봉 저장소 |
| `runtime/finrlx/workers` | 프로세스 식별·heartbeat·실행 로그 |

소스의 기준은 현재 프로젝트 폴더입니다. 다른 프로젝트 폴더의 Python 코드나 frontend 빌드를 런타임에서 가져오지 않습니다. 운영은 통합 Champion의 선택된 가중치를 읽으며 라이브러리 패키지는 검사·교체·재추가용입니다. GGUF 엔진의 native 파일 캐시는 `runtime/finrlx/engines`에 둡니다.

runtime, 환경, frontend 의존성, 인증 정보, 원본 가중치는 GitHub에 올리지 않습니다. 운영 상태 이동은 모델과 수집기를 정상 정지한 뒤 수행합니다.
