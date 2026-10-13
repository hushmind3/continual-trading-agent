# FinRL · 메인

알고리즘 기반은 설치된 FinRL DRLAgent와 SB3입니다. 기본 선택은 SAC이며 목록과 기본값은 설치 소스에서 읽습니다.

| 파일 | 역할·진입점 |
| --- | --- |
| framework.py | 공식 환경, training_environment, train, 정책 선택·체크포인트 경로 |

## 연결

- 정책 학습: web_api → job_worker → official_cli → framework.train.
- 운영 환경과 주식거래 환경의 계약을 구분합니다. 동일 알고리즘이라고 모델 호환으로 처리하지 않습니다.
- 프론트 대응 구역: FinRL · 메인.

## 메뉴 연결 파일

finrl_menu_manager.py가 이 구역의 작은 메뉴만 import합니다.

| 화면 | 연결 파일 | 프론트 담당 파일 |
| --- | --- | --- |
| 정책 학습 | policy_learning_menu.py | pages/training/TrainingWorkspace.tsx |
| FinRL 모듈 · 도구 | finrl_tools_menu.py | pages/frameworks/FrameworkWorkspace.tsx |

Champion 학습은 identity.algorithm과 요청 algorithm의 일치를 확인하며 해당 공식 SB3 모델을 적재합니다. 새 정책 학습과 MoE 생성은 구형 저장 모델의 호환 여부를 요구하지 않습니다.



현재 작은 메뉴는 정책 학습과 FinRL 모듈·도구 2개입니다. StockTradingEnv 예제·FinRL 원형/Yahoo/전처리/분할/성과의 전용 실행 모듈 operations.py와 4개 삭제 메뉴 연결 파일은 휴지통으로 이동했습니다. 주 학습 framework.py와 공식 라이브러리는 다른 실제 사용 경로의 공통 코드입니다.
