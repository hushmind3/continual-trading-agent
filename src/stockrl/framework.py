"""Official framework entrypoints; no policy, loss, optimizer or replay implementation."""
import importlib
import importlib.util
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def finrlx(name):
    source=ROOT/'FinRL-X'
    if str(source) not in sys.path:sys.path.insert(0,str(source))
    return importlib.import_module('src.'+name)


def finrl_file(relative):
    # The upstream package __init__ eagerly imports optional brokers/agents.
    # Import the chosen official module file without rewriting its source.
    package=importlib.util.find_spec('finrl')
    path=Path(package.origin).parent/relative
    name='official_finrl_'+relative.replace('/','_').removesuffix('.py')
    if name in sys.modules:return sys.modules[name]
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


def training_environment(frame,registry,training=True):
    from .expert_observation import ExpertObservation
    processor=finrl_file('meta/data_processors/processor_yahoofinance.py').YahooFinanceProcessor()
    config=finrl_file('config.py')
    if frame.date.nunique()<252:raise ValueError('FinRL 원본 turbulence 기본 기간 252개 이상의 실제 날짜가 필요합니다.')
    data=frame.rename(columns={'symbol':'tic','date':'timestamp'}).copy()
    data=processor.add_technical_indicator(data,config.INDICATORS)
    data=processor.add_turbulence(data)
    data['date']=data.timestamp
    prices,technical,turbulence=processor.df_to_array(data,config.INDICATORS,False)
    env_type=finrl_file('meta/env_stock_trading/env_stocktrading_np.py').StockTradingEnv
    env=env_type({'price_array':prices,'tech_array':technical,'turbulence_array':turbulence,'if_train':training})
    wrapped=ExpertObservation(env,registry,frame,sorted(data.tic.unique()))
    wrapped.currency='KRW' if any(str(s).endswith(('.KS','.KQ')) for s in wrapped.symbols) else 'USD'
    return wrapped


def train(frame,registry,total_timesteps,resume=False):
    from stable_baselines3 import SAC
    from stable_baselines3.common.logger import configure
    from stable_baselines3.common.callbacks import CheckpointCallback
    env=training_environment(frame,registry)
    # Select the official FinRL SAC configuration verbatim; all remaining SB3
    # settings and the original MlpPolicy/Actor/Critic/Adam/Replay are defaults.
    config=finrl_file('config.py')
    root=ROOT/'runtime/official';root.mkdir(parents=True,exist_ok=True)
    from .state_io import read_json,atomic_json
    identity={'currency':env.currency,'symbols':env.symbols}
    try:
        if resume and read_json(root/'dataset.json')!=identity:raise ValueError('저장된 정책과 통화·종목 구성이 다릅니다. 새 학습으로 시작하세요.')
        model=SAC.load(root/'sac.zip',env=env) if resume else SAC('MlpPolicy',env,**config.SAC_PARAMS)
        if resume:model.load_replay_buffer(root/'replay.pkl')
        model.set_logger(configure(str(root),['stdout','csv']))
        print('공식 SAC 시작:',model.policy.net_arch,config.SAC_PARAMS,flush=True)
        model.learn(total_timesteps=total_timesteps,reset_num_timesteps=not resume,
            callback=CheckpointCallback(save_freq=1000,save_path=str(root/'checkpoints'),name_prefix='sac',save_replay_buffer=True),progress_bar=True)
        model.save(root/'sac')
        model.save_replay_buffer(root/'replay.pkl')
        atomic_json(identity,root/'dataset.json')
        print('학습 완료:',model.num_timesteps,'관측,',model._n_updates,'업데이트',flush=True)
    finally:env.close()
    return model


def prices(currency='USD',symbols=None):
    import pandas as pd
    store=finrlx('data.data_store').DataStore()
    import sqlite3
    with sqlite3.connect(store.db_path) as connection:
        available=pd.read_sql_query('SELECT DISTINCT ticker FROM price_data',connection).ticker.tolist()
    import json
    market=json.loads((ROOT/'configs/instruments.json').read_text(encoding='utf8'))
    allowed={i['symbol'] for i in market['instruments'] if i.get('market') in (('KRX','KOSDAQ') if currency=='KRW' else ('US','NASDAQ','NYSE','NYSEARCA','AMEX')) and i.get('asset_class') in ('equity','etf')}
    names=symbols or [s for s in available if s in allowed]
    data=store.get_price_data(names,'1900-01-01','2100-01-01')
    data=data.rename(columns={'tic':'symbol','datadate':'date','prcod':'open','prchd':'high','prcld':'low','prccd':'close','cshtrd':'volume'})
    data['date']=pd.to_datetime(data.date,utc=True).dt.tz_localize(None)
    return data


def backtest(frame,registry):
    """Convert original environment holdings to the official StrategyResult API."""
    import pandas as pd
    from stable_baselines3 import SAC
    env=training_environment(frame,registry,training=False)
    try:
        from .state_io import read_json
        if read_json(ROOT/'runtime/official/dataset.json')!={'currency':env.currency,'symbols':env.symbols}:raise ValueError('저장된 정책과 통화·종목 구성이 다릅니다.')
        model=SAC.load(ROOT/'runtime/official/sac.zip',env=env)
        observation,_=env.reset();records=[]
        while True:
            action,_=model.predict(observation,deterministic=True)
            observation,_,terminated,truncated,_=env.step(action)
            base=env.unwrapped
            records.append([pd.Timestamp(env.dates[base.day]),*(base.stocks*base.price_ary[base.day]/base.total_asset)])
            if terminated or truncated:break
        weights=pd.DataFrame(records,columns=['date',*env.symbols]).set_index('date')
        result=finrlx('strategies.base_strategy').StrategyResult('Official SAC',weights)
        module=finrlx('backtest.backtest_engine')
        config=module.BacktestConfig(str(frame.date.min().date()),str(frame.date.max().date()))
        prices_wide=frame.pivot(index='date',columns='symbol',values='close')
        evaluated=module.BacktestEngine(config).run_backtest(result.strategy_name,prices_wide,result.weights)
        return evaluated
    finally:env.close()
