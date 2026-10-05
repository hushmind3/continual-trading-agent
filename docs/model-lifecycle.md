# TradingMoE 실행 수명주기

`POST /api/start`는 시장 Feed만 시작합니다. Champion과 Candidate는 각각의
시작/정지 API로 독립 실행하며, 둘 다 끈 채 Feed만 켤 수 있습니다.

두 역할은 같은 TradingMoE worker 구현을 사용하되 모델 적재, 계좌, optimizer,
replay 상태는 역할별로 분리합니다. 시작은 저장된 상태에서 이어가고 정지는
현재 작업을 마친 뒤 상태를 저장하고 해당 worker만 내립니다.

자동조립은 Candidate 실행 슬롯을 시험에 재사용합니다. 시험 계좌와 장기 운영
계좌는 분리되며, 후보마다 큰 expert checkpoint를 복제하지 않습니다.

`src/stockrl/online/`은 구형 학습기가 아니라 기존 pickle replay의 모듈 경로를
읽기 위한 호환 shim입니다. 저장 경험을 복구하려고 유지합니다.
