from pathlib import Path

root = Path(r'C:\Users\hushm\Desktop\금융매매모델')
old = 'vendor/FinRL-X'
new = 'backend/stockrl/finrl_trading/library/finrl_x'
files = [
    'backend/stockrl/finrl_trading/__init__.py',
    'backend/stockrl/platform/framework_operations.py',
    'scripts/install_windows.py', 'scripts/start_server.py', 'scripts/README.md',
]
callers = [
    'backend/stockrl/finrl/policy_learning/handlers.py',
    'backend/stockrl/finrl/policy_learning/official_cli.py',
    'backend/stockrl/management/backend_browser/handlers.py',
    'backend/stockrl/trading/control/operations_runtime.py',
    'backend/stockrl/platform/framework_operations.py',
    'backend/stockrl/platform/expert_inference.py',
    'backend/stockrl/platform/library_operations.py',
    'backend/stockrl/platform/system_operations.py',
    'backend/stockrl/platform/README.md',
]
for name in dict.fromkeys(files + callers):
    p = root / name
    text = p.read_text(encoding='utf-8')
    text = text.replace(old, new)
    text = text.replace('finrl_trading.data import', 'finrl_trading.price_data.operations import')
    text = text.replace('finrl_trading.operations', 'finrl_trading.provider_settings.operations')
    if name.endswith('framework_operations.py'):
        needle = "            if framework=='Platform':folders[:]=[]"
        assert needle in text
        text = text.replace(needle, needle + "\n            if framework=='stockrl':folders[:]=[folder for folder in folders if folder!='finrl_x']")
    p.write_text(text, encoding='utf-8', newline='\n')

p = root / 'backend/stockrl/finrl_trading/price_data/operations.py'
text = p.read_text(encoding='utf-8').replace('from .. import ROOT', 'from ... import ROOT').replace('from . import finrlx', 'from .. import finrlx')
p.write_text(text, encoding='utf-8', newline='\n')
p = root / 'backend/stockrl/finrl_trading/provider_settings/operations.py'
p.write_text(p.read_text(encoding='utf-8').replace('from . import finrlx', 'from .. import finrlx'), encoding='utf-8', newline='\n')

base = root / 'backend/stockrl/finrl_trading'
for name in ('price_data', 'provider_settings'):
    (base / name / '__init__.py').write_text('"""FinRL-Trading shared integration component."""\n', encoding='utf-8')
(base / 'README.md').write_text('''# FinRL-Trading 공통 백엔드

금융 대메뉴가 사용하는 공식 소스와 연결 모듈입니다. 독립 대메뉴·신규 화면은 등록하지 않습니다.

| 폴더 | 역할·진입점 |
| --- | --- |
| price_data/ | operations.prices: 중앙 학습·운영의 저장 가격 조회 |
| provider_settings/ | operations: 공통 공급원 인증 설정 조회·저장 |
| library/ | 수정하지 않은 공식 FinRL-X 서브모듈 |

__init__.py의 finrlx(name)가 library/finrl_x/에서 공식 모듈을 지연 import합니다. 각 소비 메뉴의 구현이 연결 모듈을 호출하며, 메뉴 등록·단일 API 계층은 유지합니다. React 화면은 frontend/src/pages/finance/에 있습니다.
폴더 이동 완료. 모델·가격·계좌·인증과 공식 알고리즘은 변경하지 않았으며 이번 작업의 실행 검사는 미실행입니다.
''', encoding='utf-8')
(base / 'price_data/README.md').write_text('''# 저장 가격 조회

- 핵심 파일·진입점: operations.py의 prices(currency, symbols).
- 사용처: 금융 policy_learning, trading/control 및 platform의 공식 함수 실행·Expert 추론.
- 필수 의존성: 상위 finrlx → 공식 data.data_store, pandas, SQLite, stockrl.ROOT.
- 보호 대상: 기존 data/·runtime/ 가격 자료를 그대로 사용합니다.
- 상태: import 경로 재배치 완료. 실제 학습·추론·가격 조회 검사는 미실행입니다.
''', encoding='utf-8')
(base / 'provider_settings/README.md').write_text('''# 공급원 설정 연결

- 핵심 파일·진입점: operations.py의 provider_environment, provider_status, save_provider.
- 사용처: management/backend_browser, platform/framework_operations·system_operations.
- 필수 의존성: 상위 finrlx → 공식 config.settings; management/connection_settings/provider_credentials의 기존 인증 저장소.
- 프론트: 기존 금융 연결·설정 화면을 사용하며 별도 메뉴를 만들지 않습니다.
- 상태: import 경로 재배치 완료. 실제 공급원 인증·시세 수신 검사는 미실행입니다.
''', encoding='utf-8')
(base / 'library/README.md').write_text('''# 공식 FinRL-X 원본

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
''', encoding='utf-8')
p = root / 'pyproject.toml'
text = p.read_text(encoding='utf-8')
text = text.replace('exclude = ["rea.project_explorer.saved_projects", "rea.project_explorer.saved_projects.*"]', 'exclude = ["rea.project_explorer.saved_projects", "rea.project_explorer.saved_projects.*", "stockrl.finrl_trading.library", "stockrl.finrl_trading.library.*"]')
p.write_text(text, encoding='utf-8', newline='\n')
p = root / 'README.md'
text = p.read_text(encoding='utf-8').replace('| [vendor/](vendor/README.md) | 수정하지 않는 공식 외부 소스 |', '| [공식 금융 소스](backend/stockrl/finrl_trading/library/README.md) | 백엔드 내부의 FinRL-X 원본 |').replace('backend/·frontend/·vendor/', 'backend/·frontend/')
p.write_text(text, encoding='utf-8', newline='\n')
p = root / 'docs/finrl_x_components.md'
text = p.read_text(encoding='utf-8').replace('현재 원본은 src/ 아래', '현재 원본은 backend/stockrl/finrl_trading/library/finrl_x/src/ 아래').replace('stockrl.finrl_trading.data.prices', 'stockrl.finrl_trading.price_data.operations.prices').replace('stockrl.finrl_trading.operations', 'stockrl.finrl_trading.provider_settings.operations')
text = text.replace('분리 단위와 프로젝트에 저장하는 방식이 확정되기 전에는 공식 서브모듈 코드를 재배치하지 않습니다. 실행·학습·백테스트·진단 검사는 미실행입니다.', '''## 적용 결과

- 공식 저장소를 vendor/FinRL-X에서 금융 백엔드의 library/finrl_x로 이동했습니다. 기존 8개 원본 영역 폴더·공식 소스·서브모듈 커밋은 유지했습니다.
- 가격 조회 연결은 price_data/operations.py, 공급원 설정 연결은 provider_settings/operations.py로 나누고 각 폴더에 README를 배치했습니다.
- 소비 모듈 import, 설치·서버 적용 경로, 공식 함수 카탈로그 경로를 함께 수정했습니다. 공식 소스를 금융 자체 모듈로 중복 집계하거나 Python 패키지로 중복 설치하지 않습니다.
- React 화면은 기존 frontend/src/pages/finance/에 유지합니다. 공식 Streamlit 코드는 원본으로만 보존하며 신규 UI·메뉴를 만들지 않았습니다.
- 실행·학습·백테스트·타입·브라우저·진단 검사는 미실행입니다. 사용자가 기존 검사 스크립트를 실행합니다.''')
p.write_text(text, encoding='utf-8', newline='\n')
print('Updated import paths, source catalog, installer, launcher, package exclusions and folder READMEs.')
