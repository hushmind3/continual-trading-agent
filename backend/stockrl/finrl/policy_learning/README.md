# 정책 학습

- 역할: menu.py: 메뉴 등록; handlers.py: 기존 API 처리. 
- 핵심 파일: handlers.py(API), menu.py(등록), official_cli.py(작업 실행), market_environment.py(가상원장 학습 환경), evaluation.py(과거 구간 비교).
- 상위 연결: ../submenu_manager.py → finance_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 새 지침 이전 CUDA SAC 학습 1,024단계·924회 업데이트와 가상원장 과거 구간 비교 완료. 최신 데이터 분할 수정 및 회귀 검사는 미실행입니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.

프론트 메뉴 주소: `#finance/policy_learning`; 화면: `frontend/src/pages/finance/finrl/policy_learning/PolicyLearning.tsx`. 백엔드 실행 모듈·API 작업명은 유지합니다.

수동 종목 선택 요청 필드를 제거했습니다. 새 정책은 해당 통화의 등록·가격 저장 종목을 사용합니다. 이어 학습은 선택된 저장 정책의 dataset.json, Champion 학습은 해당 Champion의 종목 구성으로 백엔드가 결정합니다. 작업의 symbols와 CLI --symbols는 결정된 데이터셋을 실행 프로세스에 전달하는 내부 계약입니다.

사용자가 허용한 예외로 MarketLearningEnv를 사용합니다. 공식 PortfolioOptimizationEnv 파일·FinRL/SB3 소스·알고리즘 기본값은 유지합니다. PaperAccount의 수수료·슬리피지·체결 원장을 메모리 안에서 재사용하며 실제 계좌 기록을 수정하지 않습니다. 의사결정 다음 봉에서 체결하고 비용 반영 자산 증가율의 로그를 보상으로 사용합니다. 미상장·미관측 종목은 관측 마스크로 구분하며 가격을 만들지 않습니다.

최초 학습과 평가는 시간순으로 분리합니다. 1년 미만 데이터는 같은 80% 경계를 사용해 겹침을 방지하고, 이어 학습은 최신 완료 봉을 포함합니다. Frozen Expert는 선택된 패키지만 지연 적재하며 원본 가중치를 학습하지 않습니다. 새 운영 정책 활성화·미국 가격·장중 지속학습 전체 흐름은 미완료입니다.

비교 평가 진입점은 official_cli.py의 evaluate 명령입니다. 결과 JSON은 후보 Champion의 모델 폴더에 저장합니다. 과거 가상원장 결과는 실제 거래나 미래 수익의 증명이 아닙니다.

저장 모델 목록·로드·다운로드는 실제 ZIP, 현재 환경의 dataset.json, 연결된 Champion PT 파일의 존재를 확인합니다. 삭제된 Champion의 남은 ZIP과 구형 환경 기록은 선택 모델로 등록하지 않습니다. PT 삭제·생성·변경도 목록 캐시 서명에 반영합니다. 모델 파일·선택 설정은 정리 과정에서 삭제하거나 변경하지 않습니다.

사용자 회귀 검사(미실행): PowerShell에서 `$env:PYTHONPATH='backend;development/tests'` 설정 후 `.\.venv\Scripts\python.exe -B -m unittest test_state_integrity.CheckpointAvailabilityTests`를 실행합니다. 임시 테스트 파일에서 PT/ZIP 삭제 및 구형 환경 제외를 확인하며 실제 모델 파일은 변경하지 않습니다.

학습 환경·분할·체결 회귀 검사(최신 수정 후 미실행): 위 PYTHONPATH 설정 후 `.\.venv\Scripts\python.exe -B -m unittest test_market_learning test_expert_lazy_loading test_training_cli`를 사용합니다. 실제 모델 생성·학습을 실행하는 명령과 구분합니다.
