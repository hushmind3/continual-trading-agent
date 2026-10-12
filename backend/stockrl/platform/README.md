# 공통 상태·운영·프로젝트 확장

FinRL과 FinRL-Trading의 실행 코드는 각 전용 폴더에 있습니다. 이 폴더는 단일 API, 공통 상태와 프로젝트 운영을 관리합니다.

| 파일 | 담당 |
| --- | --- |
| system_operations.py | SystemOperations: 상태 보관·작업·모델/Registry 캐시·시작/중지/적용 |
| framework_operations.py | 공통 등록·요청 중계·native_call·결과 직렬화·실행 기록·모듈 목록 |
| operations_runtime.py | 시세 입력·판단·가상계좌·지속학습 연결 |
| operations_settings.py | 기존 운영 설정 |
| sac_champion.py | 프로젝트 SAC·MoE 구성·모델 구조 |
| assets.py, expert_inference.py | Expert 자산·입력·추론 연결 |
| expert_conversion.py, library_operations.py | 등록·검사·변환·최적화 작업 |

## 연결

- framework_operations의 등록표는 요청 중계용입니다. 알고리즘을 병합하거나 재구현하지 않습니다.
- FinRL 요청은 finrl.operations, 보조 요청은 finrl_trading.operations로 전달합니다.
- 상태 조회는 SystemOperations 한 곳에서 관리하며 이미 적재한 모델을 재사용합니다.
- 프론트 대응: 거래 운영, 프로젝트 확장, 연결·관리. 프레임워크 실행 목록은 해당 구역에 따로 표시합니다.
