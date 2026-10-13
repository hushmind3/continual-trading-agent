# 공통 상태·운영·프로젝트 확장

FinRL과 FinRL-Trading의 실행 코드는 각 전용 폴더에 있습니다. 이 폴더는 단일 API, 공통 상태와 프로젝트 운영을 관리합니다.

| 파일 | 담당 |
| --- | --- |
| system_operations.py | SystemOperations: 상태 보관·작업·모델/Registry 캐시·시작/중지/적용 |
| framework_operations.py | 공통 등록·요청 중계·native_call·결과 직렬화·실행 기록·모듈 목록 |
| operations_runtime.py | 시세 입력·판단·가상계좌·지속학습 연결 |
| operations_settings.py | 기존 운영 설정 |
| sac_champion.py | 선택 알고리즘의 MoE 구성·모델 구조 |
| assets.py, expert_inference.py | Expert 자산·입력·추론 연결 |
| expert_conversion.py, library_operations.py | 등록·검사·변환·최적화 작업 |

## 연결

- framework_operations의 등록표는 요청 중계용입니다. 알고리즘을 병합하거나 재구현하지 않습니다.
- 정책 학습은 finrl.framework, 보조 등록 실행은 finrl.provider_settings.operations로 전달합니다. 제거한 FinRL 전용 실행 등록은 중계하지 않습니다.
- 상태 조회는 SystemOperations 한 곳에서 관리하며 이미 적재한 모델을 재사용합니다.
- Champion 파일을 외부에서 삭제하면 다음 통합 상태·Champion 목록 조회에서 해당 파일의 상태·서명·오류·갱신 시각 캐시를 제거합니다. 존재하는 파일의 형식 오류와 다른 모듈 오류는 유지합니다.
- Champion 목록의 파일 서명은 SAC만이 아니라 모든 알고리즘의 `*_champion_*.pt` 파일을 포함합니다.
- 시세 공급원별로 없는 필드는 표 병합 후 `None`으로 처리합니다. 선택적 bid/ask·거래 수 필드가 `NaN`으로 시세 상태나 스프레드 관측에 섞이지 않도록 합니다.
- 프론트 대응: 거래 운영, 프로젝트 확장, 연결·관리. 프레임워크 실행 목록은 해당 구역에 따로 표시합니다.

메뉴 요청 분배는 상위 menu_registry.py가 담당합니다. SystemOperations는 상태·작업·모델 캐시와 공통 명령 목록을 유지합니다.

menu_catalog는 action의 큰 메뉴·작은 메뉴 소속과 동적 framework API의 실제 입력 필드를 제공합니다. native_call의 환경·메서드 연결·CLI 인자는 기존 계약 그대로 전달합니다.

MoE Champion 생성은 요청 algorithm의 공식 DRLAgent 모델·기본 설정을 사용합니다. A2C/PPO는 정책·가치 출력, DDPG/TD3/SAC는 정책·Critic 출력, TQC는 분위수 Critic 출력, CrossQ는 Target 없이 Critic 출력을 확인하고 Replay는 지원 알고리즘만 저장합니다. Champion 형식은 finrlx_compositional_policy_champion_v1이며 알고리즘별 버전·체크포인트를 사용합니다.

## 키움 SDK 격리

`kiwoom_data.BrokerStreams`는 `.venv/kiwoom`의 `kiwoom_worker` 자식 프로세스로 SDK를 실행합니다. stdin/stdout의 `stockrl-kiwoom-v1` JSON 이벤트가 기존 시세 수집기에 전달되며 추가 HTTP 서버는 없습니다. 인증은 자식의 OS keyring에서 읽고 이벤트에는 인증 정보를 넣지 않습니다. 주 환경 Alpaca의 websockets 10.4와 SDK의 15.0.1 요구를 분리하며 종료 시 자식도 정리합니다. SDK import 검사는 `python -m stockrl.platform.kiwoom_worker --check`로 실행합니다.

원본 포트폴리오 주식 Expert의 입력은 관측 시점 이전 데이터에서 전체 학습 종목이 모두 존재하는 가장 최근 공통 일봉을 선택합니다. 서로 다른 날짜를 섞거나 빠진 가격을 채우지 않습니다. 공통 일봉이 없으면 입력 오류를 반환합니다.

FinRL-Trading 보조 등록 실행은 5개만 중계합니다. 제거한 13개 action은 등록·명령 카탈로그와 실행 라우팅에 포함하지 않습니다. csv_input은 원본 native_call의 CSV 입력에서도 쓰므로 유지하며 삭제된 전용 실행에서는 더 이상 참조하지 않습니다.
