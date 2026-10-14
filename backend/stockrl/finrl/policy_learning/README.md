# 정책 학습

- 역할: menu.py: 메뉴 등록; handlers.py: 기존 API 처리. 
- 핵심 파일: handlers.py(API), menu.py(등록), official_cli.py(작업 실행), market_environment.py(가상원장 학습 환경), evaluation.py(과거 구간 비교).
- 상위 연결: ../submenu_manager.py → finance_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 사용자가 이번 변경 묶음의 검사 실행을 별도로 허용한 뒤 백엔드 전체 102개 검사 통과. 실제 이어 학습 32단계와 1단계가 각각 종료돼 누적 1,057단계·957회 업데이트를 확인했습니다. CUDA 추론과 다음 봉의 가상원장 체결도 확인했습니다. 운영 정책은 자동 변경하지 않았습니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.

프론트 메뉴 주소: `#finance/policy_learning`; 화면: `frontend/src/pages/finance/finrl/policy_learning/PolicyLearning.tsx`. 백엔드 실행 모듈·API 작업명은 유지합니다.

수동 종목 선택 요청 필드를 제거했습니다. 새 정책은 해당 통화의 등록·가격 저장 종목을 사용합니다. 이어 학습은 선택된 저장 정책의 dataset.json, Champion 학습은 해당 Champion의 종목 구성으로 백엔드가 결정합니다. 작업의 symbols와 CLI --symbols는 결정된 데이터셋을 실행 프로세스에 전달하는 내부 계약입니다.

사용자가 허용한 예외로 MarketLearningEnv를 사용합니다. 공식 PortfolioOptimizationEnv 파일·FinRL/SB3 소스·알고리즘 기본값은 유지합니다. PaperAccount의 수수료·슬리피지·체결 원장을 메모리 안에서 재사용하며 실제 계좌 기록을 수정하지 않습니다. 의사결정 다음 봉에서 체결하고 비용 반영 자산 증가율의 로그를 보상으로 사용합니다. 미상장·미관측 종목은 관측 마스크로 구분하며 가격을 만들지 않습니다.

최초 학습과 평가는 시간순으로 분리합니다. 1년 미만 데이터는 같은 80% 경계를 사용해 겹침을 방지하고, 이어 학습은 최신 완료 봉을 포함합니다. Frozen Expert는 선택된 패키지만 지연 적재하며 원본 가중치를 학습하지 않습니다. 새 운영 정책 활성화·미국 가격·장중 지속학습 전체 흐름은 미완료입니다.

비교 평가 진입점은 official_cli.py의 evaluate 명령입니다. 결과 JSON은 후보 Champion의 모델 폴더에 저장합니다. 과거 가상원장 결과는 실제 거래나 미래 수익의 증명이 아닙니다.

저장 모델 목록은 해당 체크포인트와 일치하며 체크포인트보다 오래되지 않은 평가 JSON에서 요약 지표만 전달합니다. 화면 조회는 모델 생성·학습·평가를 실행하지 않습니다. 지속학습은 실제 소비 봉 이후 입력이 있을 때만 예약하며, 직전 실행 시간과 처리량으로 다음 작업량을 제한합니다. 이어 학습의 입력 끝은 시간 제한으로 처리하고 유한한 비교 평가의 종료와 구분합니다. 이번 수정 과정에서 새 학습 작업은 실행하지 않았습니다.

저장 모델 목록·로드·다운로드는 실제 ZIP, 현재 환경의 dataset.json, 연결된 Champion PT 파일의 존재를 확인합니다. 삭제된 Champion의 남은 ZIP과 구형 환경 기록은 선택 모델로 등록하지 않습니다. PT 삭제·생성·변경도 목록 캐시 서명에 반영합니다. 모델 파일·선택 설정은 정리 과정에서 삭제하거나 변경하지 않습니다.

사용자 회귀 검사(미실행): PowerShell에서 `$env:PYTHONPATH='backend;development/tests'` 설정 후 `.\.venv\Scripts\python.exe -B -m unittest test_state_integrity.CheckpointAvailabilityTests`를 실행합니다. 임시 테스트 파일에서 PT/ZIP 삭제 및 구형 환경 제외를 확인하며 실제 모델 파일은 변경하지 않습니다.

학습 환경·분할·체결 회귀 검사: 위 PYTHONPATH 설정 후 `.\.venv\Scripts\python.exe -B -m unittest test_market_learning test_expert_lazy_loading test_training_cli`를 사용합니다. 이번 변경 묶음은 전체 102개 검사에 포함해 통과했습니다. 실제 모델 생성·학습을 실행하는 명령과 구분합니다.

가격 주기: RunRequest.timeframe과 CLI --timeframe은 1d/1m을 지원합니다. 새 학습의 기본값은 기존 일봉이며, 이어 학습은 저장 정책의 주기를 상속합니다. 다른 주기의 이어 학습·Replay 혼합·비교 평가는 거부합니다. dataset.json·새 Champion의 identity에 주기를 기록하고 training_input에는 실제 출처·주기를 남깁니다. 분봉 입력은 수신 완료된 봉만 사용합니다. 단위 검사와 브라우저 주기 전달 검사는 통과했습니다. 실제 일봉 이어 학습은 확인했고, 새로운 실시간 분봉 수신부터 학습까지의 실행은 아직 확인하지 않았습니다.

소비 범위: training_input.end는 읽은 입력의 최신 시각입니다. consumed_end는 환경 step이 실제로 소비한 마지막 시각이며 transitions는 이번 작업에서 실행한 전이 수입니다. 에피소드 reset으로 이 누적 기록을 지우지 않습니다. 이어 학습은 consumed_end 다음 봉부터 진행하도록 과거 관측 문맥을 남겨 시작 위치를 정합니다. 과거 기록에 consumed_end가 없으면 end를 실제 학습 증거로 사용하지 않으며 첫 실행에서 새 소비 기록을 만듭니다. 기존 모델·JSON을 소급 변경하지 않습니다. 같은 주기의 SAC Replay 복원과 공식 학습 기본값은 유지합니다. 실제 sac_champion_003에서 소비 시각 2024-07-24를 저장했고, 다음 sac_champion_004의 1단계 학습은 2024-07-25를 소비했습니다. 입력 최신 시각은 2026-10-13으로, 남은 입력을 전부 학습했다고 주장하지 않습니다.
