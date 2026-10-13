# FinRL-Trading · 보조

공식 원본은 프로젝트 최상위 FinRL-X/입니다. 이 폴더는 필요한 보조 기능의 연결 코드이며 기본 학습기를 소유하지 않습니다.

| 파일 | 역할·진입점 |
| --- | --- |
| __init__.py | finrlx: 필요한 원본 모듈을 지연 import |
| data.py | prices: 기존 DataStore 가격 조회·일봉 구분 |
| operations.py | 보조 ACTIONS·execute; 원형 Adaptive Rotation 데이터 준비/단일 실행/백테스트·거래일·설정 유효성·공급원 보안 설정 |

## 연결

- 공통 API 중계는 ACTIONS 소유 폴더에 따라 execute를 호출합니다.
- 공급원: provider_environment, provider_status, save_provider.
- 설정·가격·비중 평가의 기존 계약과 기본값을 유지합니다.
- A2C·DDPG·PPO·TD3·SAC 알고리즘 선택·학습은 finrl/에서 담당합니다.
- 프론트 대응 구역: FinRL-Trading · 보조. 인증 설정은 공통 연결·설정 화면에서도 접근합니다.

## 메뉴 연결 파일

finrl_trading_menu_manager.py가 이 구역의 작은 메뉴만 import합니다.

| 화면 | 연결 파일 | 프론트 담당 파일 |
| --- | --- | --- |
| 보조 데이터 · 전략 · 도구 | finrl_trading_tools_menu.py | pages/frameworks/FrameworkWorkspace.tsx |

`finrlx()`는 고정된 `FinRL-X` submodule 루트와 `src`를 import 경로에 추가하고 `src.<모듈>`을 적재합니다. 원본의 `data`·`strategies` 등 절대 import를 유지합니다. 중복 `finrl-trading` 배포판 대신 이 원본을 사용하며 필요한 공급원 패키지는 운영 명세에 선언합니다. 외부 원본은 수정하지 않습니다.


정책 평가 메뉴 전용 backtest.py 어댑터는 제거했습니다. 보조 원본 도구·데이터·전략 실행과 공식 소스는 유지합니다.

ACTIONS/execute는 adaptive_download, adaptive_single, adaptive_backtest, calendar, config_check만 연결합니다. 제거한 13개 항목의 실행 분기·가격/종목 입력·CSV 처리 의존성을 삭제했습니다. 이전 operations.py와 컴파일 캐시는 휴지통에 보관하고 같은 파일에는 남은 실행·공급원 공통 코드만 유지합니다. DataStore/DataFetcher/DataProcessor/Adaptive Rotation 원본은 가격 저장·수집과 남은 원형 실행에서 사용하므로 수정하지 않습니다.
