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
- FinRL 요청은 finrl.operations, 보조 요청은 finrl_trading.operations로 전달합니다.
- 상태 조회는 SystemOperations 한 곳에서 관리하며 이미 적재한 모델을 재사용합니다.
- 프론트 대응: 거래 운영, 프로젝트 확장, 연결·관리. 프레임워크 실행 목록은 해당 구역에 따로 표시합니다.

메뉴 요청 분배는 상위 menu_registry.py가 담당합니다. SystemOperations는 상태·작업·모델 캐시와 공통 명령 목록을 유지합니다.

menu_catalog는 action의 큰 메뉴·작은 메뉴 소속과 동적 framework API의 실제 입력 필드를 제공합니다. native_call의 환경·메서드 연결·CLI 인자는 기존 계약 그대로 전달합니다.

MoE Champion 생성은 요청 algorithm의 공식 DRLAgent 모델·기본 설정을 사용합니다. A2C/PPO는 정책·가치 출력, DDPG/TD3/SAC는 정책·Critic 출력, TQC는 분위수 Critic 출력, CrossQ는 Target 없이 Critic 출력을 확인하고 Replay는 지원 알고리즘만 저장합니다. Champion 형식은 finrlx_compositional_policy_champion_v1이며 알고리즘별 버전·체크포인트를 사용합니다.
