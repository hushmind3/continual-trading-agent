# FinRL-X 운영 구조

목표 비중은 전략·잔고·가격 확인·가상체결·평가가 공유하는 계약이다. FinRL-X/FinRL-Trading의 `BaseStrategy`와 `StrategyResult` API를 사용하고, 실제 시세 수집·가상계좌·프로세스 관리·복구는 `src/stockrl/platform`과 프로젝트의 시세·계좌 모듈이 담당한다. `champion.pt`의 기존 MoE 결합부와 allocation head를 이어받고, 64D latent와 실제 시장·계좌 상태를 TorchRL Allocator에 전달한다.

```mermaid
flowchart LR
  Feed[실시간 시세 / 과거 재생] --> Obs[시점 일치 관측]
  Obs --> Expert[고정 Expert 공유 서비스]
  Expert --> MoE[Champion MoE 결합부 / 64D latent]
  MoE --> Policy[TorchRL Allocator + 실제 시장 feature]
  Policy --> Risk[통화별 잔고·가격 확인]
  Risk --> Result[FinRL-X StrategyResult]
  Result --> Paper[다음 관측에서 가상체결]
  Paper --> Reward[비용 반영 순자산 변화]
  Reward --> Journal[SQLite 경험 기록]
  Journal --> Learner[TorchRL PPO / 별도 CPU 프로세스]
  Learner --> Revision[작은 정책 버전 / 복원]
  Revision --> Policy
```


12개는 원본 자산 수이며 동시 실행 수를 뜻하지 않는다. 선택한 Expert 중 원본 입력과 자원 조건이 맞는 모델을 순회 실행한다. RAM·VRAM 조건이 부족하면 자원 대기로 표시하고 다음 실행 기회에 다시 확인한다.

종목 수는 정책 파라미터 크기와 독립적이다. 통화마다 자산 집합과 현금을 함께 판단하고, 미수신 자산은 비중을 바꾸지 않는다. 학습 경험은 종목 집합과 정책 버전이 맞는 그룹으로 처리한다.

추론 조정기는 하나이며, 큰 Expert는 단기 작업 프로세스에서 순차 실행하고 작업 완료 후 모델 매핑과 임시 메모리를 해제한다. 작은 정책은 조정기의 CPU 캐시를 사용한다. GPU에는 한 Expert만 올리고, 실제 가용 RAM·VRAM과 관측된 peak를 확인한다. 학습은 별도 CPU 프로세스에서 진행하고 추론에는 유효한 작은 정책 버전만 전달한다. 상태·경험·오류·제어는 운영 API가 관리한다. 모든 운영 설정은 `configs/operations.json`에서 읽는다.

FinRL-X upstream `4409abe925c904e570be78ebfb5e77ac3491dff8`, TorchRL `0.14.0`, TensorDict `0.14.2`, 공식 키움 SDK `953e5dbff123f437ab4d11a78a95191a685eb51f`를 사용한다. 키움 OAuth와 WebSocket 연결은 공식 SDK, 국내 체결가와 미국 FE 메시지는 시세 어댑터, 통화별 비용·정수 주식 체결은 가상계좌가 담당한다. 최종 비중은 실제 `BaseStrategy.generate_weights()`와 `StrategyResult` 계약을 통과한다.

종목별 최대 비중·총 투자 비중·turnover 제한·MDD 강제 청산은 적용하지 않는다. 목표 비중과 현금 비중은 모델이 선택한다. 손실폭은 관측 값으로 전달하며, 손익과 체결 비용으로 학습한다. 관측이 없는 보유자산과 현금 계좌의 실제 잔고는 체결 가능한 범위를 계산할 때 유지한다.

학습 배치는 같은 종목 집합과 허용된 실제 학습 세대의 경험만 묶는다. 선택 변경을 저장한 체크포인트 번호와 optimizer가 갱신된 세대를 구분한다. 화면의 다음 배치 진행도는 전체 미처리 경험 합계가 아니라 가장 많이 모인 동일 구성의 경험 수를 표시한다.

고정 Expert는 `frozen_expert_package_v1` 파일로, 구성·기존 결합부는 `registered_vertical_trading_moe_v2` 헤더로 분리한다. 헤더에는 immutable 패키지의 상대 경로·크기·SHA256을 기록한다. 최신 정책 체크포인트는 결합부·Allocator·optimizer·슬롯 선택을 포함하고, 작은 Champion 파일에도 같은 학습 상태를 원자적으로 반영한다. runtime의 정책 버전이 없으면 Champion에 저장된 상태로 복원한다. 추가 전 검사와 다운로드·패키징은 독립 작업 프로세스에서 수행한다.

슬롯마다 Adapter·Router·context Router·projection을 독립 파라미터로 둔다. 출력 크기에 맞춰 새 연결을 만들고 기존 이름의 학습 가중치·Adam moment는 유지한다. 64D 공통 attention과 최종 의사결정부는 Expert 수와 독립적이다. 기존 슬롯 선택은 실시간 제어 파일과 작은 체크포인트로 적용하며 추론·학습 프로세스를 재시작하지 않는다.

경험에는 실제 사용한 Expert 마스크가 관측으로 남는다. 현재 제외된 Expert가 있어도 당시 행동의 likelihood를 당시 마스크로 계산한다. 제외된 슬롯의 전용 파라미터는 optimizer에서 갱신하지 않으며, 재사용할 때 그대로 이어받는다. 새로운 입출력 슬롯 추가·실제 삭제는 자동으로 모든 저장 정책의 구조를 맞추고 호환되지 않는 미처리 경험을 제외한다.

Allocator는 정규분포의 잠재 점수를 표본 추출하고 sparsemax로 자산·현금 비중을 계산한다. 비중 0을 허용하며 종목 수에 고정 상한을 두지 않는다. PPO에는 원래 표본 추출한 잠재 행동과 log probability를 기록하므로, 실제 reward와 다른 임의의 행동을 학습하지 않는다. 기존 MoE·Allocator 가중치와 이름이 같은 parameter의 Adam 상태를 정책 전환 시 이어받는다.

KRW와 USD 계좌의 현금·포지션·손익·모델 계좌 특성·reward·체결 원장은 분리한다. 두 금액의 환전 합계는 제공하지 않는다. 새 체결 원장은 계좌·경험 처리와 같은 transaction에서 기록하며, 통화와 체결 순번을 기준으로 조회한다. bounded 계좌 미리보기에서 기록이 빠져도 체결 원장은 유지한다. 원장이 없는 과거 체결은 누적 카운터와 구분해 누락 건수로 표시한다.
