"""FinRL-Trading supplementary data, strategy and provider operations."""
import subprocess
import sys
from pathlib import Path
from .. import ROOT
from . import finrlx
from .data import prices
from ..state_io import atomic_json

ACTIONS={
    'adaptive_download':('Adaptive Rotation 원형 데이터 준비', 'workflows', 'FinRL-X:deploy', 'deploy.sh::data download', ['config_path', 'data_dir']),
    'adaptive_single':('Adaptive Rotation 원형 단일 실행', 'workflows', 'FinRL-X:strategies.run_adaptive_rotation_strategy', 'run_single_date', ['config_path', 'data_dir', 'as_of_date']),
    'adaptive_backtest':('Adaptive Rotation 원형 전체 백테스트', 'workflows', 'FinRL-X:strategies.run_adaptive_rotation_strategy', 'run_backtest', ['config_path', 'data_dir', 'start_date', 'end_date']),
    'calendar':('시장 거래일', 'markets', 'FinRL-X:data.trading_calendar', 'get_trading_days', ['start_date', 'end_date', 'exchange']),
    'fundamentals':('FMP 재무 데이터 수집', 'markets', 'FinRL-X:data.data_fetcher', 'fetch_fundamental_data', ['symbols', 'start_date', 'end_date']),
    'news':('FMP 뉴스 수집', 'markets', 'FinRL-X:data.data_fetcher', 'fetch_news', ['symbol', 'start_date', 'end_date']),
    'nasdaq100':('NASDAQ 100 조회', 'markets', 'FinRL-X:data.data_fetcher', 'fetch_nasdaq100_tickers', []),
    'sp500':('S&P 500 조회', 'markets', 'FinRL-X:data.data_fetcher', 'fetch_sp500_tickers', []),
    'process_prices':('공식 가격 CSV 전처리', 'markets', 'FinRL-X:data.data_processor', 'process_prices', ['source']),
    'process_fundamentals':('공식 재무 CSV 전처리', 'markets', 'FinRL-X:data.data_processor', 'process_fundamentals', ['source']),
    'ml_dataset':('공식 ML 데이터 구성', 'markets', 'FinRL-X:data.data_processor', 'create_ml_dataset', ['fundamentals', 'source', 'target_period']),
    'tsmom':('공식 TSMOM 신호', 'markets', 'FinRL-X:strategies.tsmomsignal', 'TSMOMSignalEngine.generate_signal_one_ticker', ['currency', 'symbols']),
    'adaptive':('공식 Adaptive Rotation', 'portfolio', 'FinRL-X:strategies.adaptive_rotation.adaptive_rotation_engine', 'AdaptiveRotationEngine.run', ['currency', 'symbols', 'config_path', 'as_of_date']),
    'equal_weight':('공식 동일 비중 전략', 'portfolio', 'FinRL-X:strategies.base_strategy', 'EqualWeightStrategy.generate_weights', ['fundamentals']),
    'ml':('공식 ML 종목 선택', 'portfolio', 'FinRL-X:strategies.ml_strategy', 'MLStockSelectionStrategy.generate_weights', ['fundamentals', 'source', 'prediction_mode', 'weight_method']),
    'sector_ml':('공식 산업별 ML 종목 선택', 'portfolio', 'FinRL-X:strategies.ml_strategy', 'SectorNeutralMLStrategy.generate_weights', ['fundamentals', 'source', 'prediction_mode', 'weight_method']),
    'performance':('공식 수익·성과 지표', 'portfolio', 'FinRL-X:trading.performance_analyzer', 'compute_performance_metrics', ['currency', 'symbol']),
    'config_check':('FinRL-X 설정 유효성', 'connection', 'FinRL-X:config.settings', 'validate_config', []),
}

PROVIDER_FIELDS={
    'FMP':['FMP_API_KEY'],
    'Alpaca':['APCA_API_KEY','APCA_API_SECRET','APCA_BASE_URL'],
    'WRDS':['WRDS_USERNAME','WRDS_PASSWORD'],
}

def provider_environment():
    from ..provider_credentials import _vault
    vault=_vault()
    return {key:value for keys in PROVIDER_FIELDS.values() for key in keys
        if (value:=vault.get_password('stockrl.official-framework',key))}

def provider_status():
    import os
    saved=provider_environment();config=finrlx('config.settings').get_config()
    existing={'FMP':bool(config.fmp.api_key),'Alpaca':bool(config.alpaca.api_key and config.alpaca.api_secret),
              'WRDS':bool(config.wrds.username and config.wrds.password)}
    return {'items':[{'name':name,'fields':keys,'configured':existing[name] or all(saved.get(key) or os.environ.get(key) for key in keys if not key.endswith('BASE_URL')),
        'status':'설정 여부만 확인 · 실제 인증·수신 미확인'} for name,keys in PROVIDER_FIELDS.items()]}

def save_provider(name,values):
    import os
    from ..provider_credentials import _vault
    if name not in PROVIDER_FIELDS:raise ValueError('공식 공급원 설정을 선택하세요.')
    vault=_vault()
    for key,value in values.items():
        if key not in PROVIDER_FIELDS[name]:raise ValueError('원본 공급원 환경변수 이름이 아닙니다: '+key)
        if value:vault.set_password('stockrl.official-framework',key,str(value))
    os.environ.update(provider_environment());finrlx('config.settings').reload_config()
    return provider_status()

def execute(action, parameters, output):
    from ..platform.framework_operations import csv_input,serialize
    import pandas as pd
    if action not in ACTIONS:
        raise ValueError('등록된 공식 실행 기능이 아닙니다.')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    p = {key: value for key, value in parameters.items() if value not in ('', None, [])}
    row = ACTIONS[action]
    if action == 'adaptive_download':
        import re
        script = ROOT / 'FinRL-X/deploy.sh'
        source = script.read_text(encoding='utf-8')
        match = re.search('python3 - "\\$CONFIG" "\\$DATA_DIR" <<\\x27PYEOF\\x27\\n(.*?)\\nPYEOF', source, re.S)
        if not match:
            raise ValueError('공식 deploy.sh의 데이터 준비 실행 블록을 찾지 못했습니다.')
        config = str(Path(p.get('config_path', ROOT / 'FinRL-X/src/strategies/AdaptiveRotationConf_v1.2.1.yaml')).resolve())
        directory = Path(p.get('data_dir', ROOT / 'FinRL-X/data/fmp_daily')).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        print('공식 deploy.sh 데이터 준비 블록 실행:', directory, flush=True)
        subprocess.run([sys.executable, '-', config, str(directory)], input=match.group(1), text=True, encoding='utf-8', cwd=ROOT / 'FinRL-X', check=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return {'action': action, 'module': row[2], 'function': row[3], 'value': {'data_dir': str(directory), 'config': config}, 'output': str(output.relative_to(ROOT))}
    module = finrlx(row[2].split(':', 1)[1])
    currency = p.get('currency', 'USD')
    symbols = p.get('symbols') or ([p['symbol']] if p.get('symbol') else None)
    if isinstance(symbols, str):
        symbols = [s.strip() for s in symbols.split(',') if s.strip()]
    print('공식 함수 실행:', row[2], row[3], flush=True)
    if action in ('adaptive_single', 'adaptive_backtest'):
        config = str(Path(p.get('config_path', ROOT / 'FinRL-X/src/strategies/AdaptiveRotationConf_v1.2.1.yaml')).resolve())
        kwargs = {'data_dir': p['data_dir']} if p.get('data_dir') else {}
        from contextlib import chdir
        with chdir(ROOT / 'FinRL-X'):
            if action == 'adaptive_single':
                value = module.run_single_date(config, p['as_of_date'], **kwargs)
            else:
                value = module.run_backtest(config, p['start_date'], p['end_date'], **kwargs)
    elif action == 'calendar':
        kwargs = {'exchange': p['exchange']} if p.get('exchange') else {}
        value = module.get_trading_days(p['start_date'], p['end_date'], **kwargs)
    elif action == 'sp500':
        value = module.fetch_sp500_tickers(output_path=str(output / 'sp500.csv'))
    elif action == 'nasdaq100':
        value = module.fetch_nasdaq100_tickers()
    elif action == 'fundamentals':
        value = module.fetch_fundamental_data(symbols, p['start_date'], p['end_date'])
    elif action == 'news':
        value = module.fetch_news(p['symbol'], p['start_date'], p['end_date'])
    elif action in ('process_prices', 'process_fundamentals'):
        source, _ = csv_input(p, 'source')
        function = module.process_prices if action == 'process_prices' else module.process_fundamentals
        value = function(str(source), str(output / 'processed.csv'))
    elif action == 'ml_dataset':
        fundamentals, _ = csv_input(p, 'fundamentals')
        source, _ = csv_input(p, 'source')
        value = module.DataProcessor(data_dir=str(output)).create_ml_dataset(str(fundamentals), str(source), **{'target_period': int(p['target_period'])} if 'target_period' in p else {})
    elif action in ('equal_weight', 'ml', 'sector_ml'):
        _, fundamentals = csv_input(p, 'fundamentals')
        data = {'fundamentals': fundamentals}
        if p.get('source'):
            _, data['prices'] = csv_input(p, 'source')
        cls = {'equal_weight': 'EqualWeightStrategy', 'ml': 'MLStockSelectionStrategy', 'sector_ml': 'SectorNeutralMLStrategy'}[action]
        config = finrlx('strategies.base_strategy').StrategyConfig()
        result = getattr(module, cls)(config).generate_weights(data, **{k: p[k] for k in ('prediction_mode', 'weight_method') if k in p})
        if result.metadata and result.metadata.get('error'):
            raise ValueError(str(result.metadata['error']))
        value = {'weights': result.weights, 'metadata': result.metadata}
    elif action == 'config_check':
        value = module.validate_config()
    else:
        frame = prices(None if action == 'adaptive' else currency, symbols)
        if frame.empty:
            raise ValueError('선택 종목의 실제 저장 가격이 없습니다.')
        if action == 'performance':
            value = module.compute_performance_metrics(frame.sort_values('date').set_index('date').close)
        elif action == 'tsmom':
            engine = module.TSMOMSignalEngine()
            value = {symbol: engine.generate_signal_one_ticker(data.rename(columns={'symbol': 'tic'})) for symbol, data in frame.groupby('symbol')}
        elif action == 'adaptive':
            config = Path(p.get('config_path', ROOT / 'FinRL-X/src/strategies/AdaptiveRotationConf_v1.2.1.yaml')).expanduser().resolve()
            if not config.is_file():
                raise ValueError('실제 Adaptive Rotation YAML 경로가 필요합니다.')
            preprocessing = finrlx('strategies.adaptive_rotation.data_preprocessor')
            calendar = finrlx('strategies.adaptive_rotation.utils.calendar_utils')
            week_ends = calendar.get_week_end_dates(str(frame.date.min().date()), str(frame.date.max().date()))
            weekly = preprocessing.aggregate_multiple_symbols_to_weekly({symbol: data.set_index('date') for symbol, data in frame.groupby('symbol')}, week_ends)
            series = {symbol: data.close for symbol, data in weekly.items()}
            weights, audit = module.AdaptiveRotationEngine(config_path=str(config)).run(series, p.get('as_of_date', str(frame.date.max().date())))
            value = {'weights': weights, 'audit': audit}
        else:
            raise ValueError('실행 어댑터가 없습니다.')
    if isinstance(value, pd.DataFrame):
        value.to_csv(output / 'result.csv', index=False)
    result = {'action': action, 'module': row[2], 'function': row[3], 'output': str(output.relative_to(ROOT)), 'value': serialize(value)}
    atomic_json(result, output / 'result.json')
    print('공식 함수 실행 완료:', row[3], flush=True)
    return result
