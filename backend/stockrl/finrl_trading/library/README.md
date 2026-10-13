# 공식 FinRL-X 원본

finrl_x/는 AI4Finance-Foundation/FinRL-Trading의 Git 서브모듈입니다. 서브모듈 이름·원격·커밋·공식 코드를 유지하고 위치만 금융 백엔드로 옮겼습니다.

| 원본 폴더 | 역할 |
| --- | --- |
| finrl_x/src/data/ | 데이터 수집·처리·저장·거래일 |
| finrl_x/src/config/ | 공급원·실행 설정 |
| finrl_x/src/strategies/ | 공식 전략 |
| finrl_x/src/backtest/ | 공식 백테스트 |
| finrl_x/src/trading/ | 브로커·주문·성과 |
| finrl_x/src/tools/ | 공식 도구 |
| finrl_x/src/utils/ | 공통 보조 함수 |
| finrl_x/src/web/ | 공식 Streamlit 원본; 플랫폼 화면·실행에 미연결 |

플랫폼 연결은 ../__init__.py의 finrlx입니다. 설치는 루트 설치.cmd가 호출하는 install_windows.py의 git submodule update --init backend/stockrl/finrl_trading/library/finrl_x입니다.
플랫폼 화면은 frontend/src/pages/finance/이며 Streamlit 원본을 React 화면으로 등록하지 않습니다. 이번 작업의 공식 함수 실행 검사는 미실행입니다.
