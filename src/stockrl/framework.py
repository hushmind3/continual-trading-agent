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


def sac_example():
    import ast,inspect
    function=finrlx('strategies.rl_model').train_sac
    tree=ast.parse(inspect.getsource(function))
    parameters=next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SAC_PARAMS' for t in n.targets))
    steps=next(ast.literal_eval(k.value) for n in ast.walk(tree) if isinstance(n,ast.Call) for k in n.keywords if k.arg=='total_timesteps')
    return function,parameters,steps


def training_environment(frame,registry,training=True,champion_ids=None):
    import numpy as np
    import pandas as pd
    from finrl import config
    from finrl.meta.preprocessor.preprocessors import FeatureEngineer
    from finrl.meta.env_portfolio_allocation.env_portfolio import StockPortfolioEnv
    from .expert_observation import ExpertObservation
    data=FeatureEngineer().preprocess_data(frame.rename(columns={'symbol':'tic'}).copy())
    data=data.sort_values(['date','tic'],ignore_index=True)
    data.index=data.date.factorize()[0]
    cov_list=[];return_list=[];lookback=252
    for i in range(lookback,len(data.index.unique())):
        prices=data.loc[i-lookback:i].pivot_table(index='date',columns='tic',values='close')
        returns=prices.pct_change().dropna()
        return_list.append(returns);cov_list.append(returns.cov().values)
    covariance=pd.DataFrame({'date':data.date.unique()[lookback:],'cov_list':cov_list,'return_list':return_list})
    data=data.merge(covariance,on='date').sort_values(['date','tic']).reset_index(drop=True)
    if data.empty:raise ValueError('원본 Portfolio 환경의 252일 공분산 입력을 만들 가격이 부족합니다.')
    data.index=data.date.factorize()[0]
    example=finrlx('strategies.rl_model')
    trade_date=frame.date.max()+pd.Timedelta(days=1)
    if training:
        data=example.prepare_rolling_train(data,'date',pd.Timedelta(days=365),pd.Timedelta(days=1095),trade_date)
    else:
        data=example.prepare_rolling_test(data,'date',pd.Timedelta(days=365),pd.Timedelta(days=1095),trade_date)
    if data.empty:raise ValueError('원본 rolling 예제의 학습·평가 구간에 데이터가 없습니다.')
    count=len(data.tic.unique())
    env=StockPortfolioEnv(df=data,stock_dim=count,hmax=100,initial_amount=1000000,
        transaction_cost_pct=0.001,reward_scaling=1e-4,state_space=count,
        action_space=count,tech_indicator_list=config.INDICATORS)
    (ROOT/'results').mkdir(exist_ok=True)
    wrapped=ExpertObservation(env,registry,frame,sorted(data.tic.unique()),champion_ids=champion_ids)
    wrapped.currency='KRW' if any(str(s).endswith(('.KS','.KQ')) for s in wrapped.symbols) else 'USD'
    return wrapped


def champion_structure_environment(currency,symbols,registry,champion_ids):
    """Build the official FinRL/SB3 spaces without requiring market history or running Experts."""
    import numpy as np
    import pandas as pd
    from finrl import config
    from finrl.meta.env_portfolio_allocation.env_portfolio import StockPortfolioEnv
    from .expert_observation import ExpertObservation
    symbols=list(symbols);count=len(symbols);stamp=pd.Timestamp('2000-01-01')
    data={'date':[stamp]*count,'tic':symbols,'close':[1.]*count,'cov_list':[np.eye(count)]*count}
    data.update({name:[0.]*count for name in config.INDICATORS})
    frame=pd.DataFrame(data);frame.index=0
    env=StockPortfolioEnv(df=frame,stock_dim=count,hmax=100,initial_amount=1000000,
        transaction_cost_pct=0.001,reward_scaling=1e-4,state_space=count,
        action_space=count,tech_indicator_list=config.INDICATORS)
    wrapped=ExpertObservation(env,registry,frame.rename(columns={'tic':'symbol'}),symbols,
        champion_ids=champion_ids,structure_only=True)
    wrapped.currency=currency
    return wrapped


def train(frame,registry,resume=False,output=None,champion_path=None,champion_output=None):
    from stable_baselines3 import SAC
    from finrl.agents.stablebaselines3.models import DRLAgent
    from .platform.sac_champion import load_spec
    champion = load_spec(champion_path) if champion_path else None
    champion_ids = champion.get('identity',{}).get('champion_experts') if champion else None
    env=training_environment(frame,registry,champion_ids=champion_ids)
    example,parameters,steps=sac_example()
    root=Path(output) if output is not None else ROOT/'runtime/official'
    if not root.resolve().is_relative_to((ROOT/'runtime/official').resolve()):raise ValueError('정책 출력은 기존 runtime/official 내부에 저장합니다.')
    root.mkdir(parents=True,exist_ok=True)
    from .state_io import read_json,atomic_json
    saved=policy_files()
    identity={'currency':env.currency,'symbols':env.symbols,'sac_example':parameters,'environment':'finrl.meta.env_portfolio_allocation.env_portfolio.StockPortfolioEnv','rolling_days':[1095,365]}
    if champion:
        identity.update(champion['identity'])
        if champion_output:identity['champion_file']=str(Path(champion_output))
    try:
        if resume and read_json(saved/'dataset.json')!=identity:raise ValueError('저장된 정책과 통화·종목 구성이 다릅니다. 새 학습으로 시작하세요.')
        agent=DRLAgent(env=env)
        print('FinRL-X 원본 SAC 예제:',parameters,'단계:',steps,flush=True)
        if champion:
            checkpoint=Path(champion['checkpoint'])
            if not checkpoint.is_absolute():checkpoint=ROOT/'runtime/official'/checkpoint
            model=SAC.load(checkpoint,env=env)
            if (checkpoint.parent/'replay.pkl').is_file():model.load_replay_buffer(checkpoint.parent/'replay.pkl')
            model=agent.train_model(model=model,tb_log_name='sac',total_timesteps=steps)
        elif resume:
            model=SAC.load(saved/'sac.zip',env=env);model.load_replay_buffer(saved/'replay.pkl')
            model=agent.train_model(model=model,tb_log_name='sac',total_timesteps=steps)
        else:model=example(agent)
        model.save(root/'sac')
        model.save_replay_buffer(root/'replay.pkl')
        atomic_json(identity,root/'dataset.json')
        if champion and champion_output:
            from .platform.sac_champion import save_trained_champion
            save_trained_champion(champion_path,model,Path(champion_output),root)
        print('학습 완료:',model.num_timesteps,'관측,',model._n_updates,'업데이트',flush=True)
    finally:env.close()
    return model


def prices(currency='USD',symbols=None):
    import pandas as pd
    store=finrlx('data.data_store').DataStore()
    import sqlite3
    with sqlite3.connect(store.db_path) as connection:
        available=pd.read_sql_query('SELECT DISTINCT ticker FROM price_data',connection).ticker.tolist()
        start,end=connection.execute('SELECT MIN(date),MAX(date) FROM price_data').fetchone()
    import json
    market=json.loads((ROOT/'configs/instruments.json').read_text(encoding='utf8'))
    allowed={i['symbol'] for i in market['instruments'] if i.get('market') in (('KRX','KOSDAQ') if currency=='KRW' else ('US','NASDAQ','NYSE','NYSEARCA','AMEX')) and i.get('asset_class') in ('equity','etf')}
    names=symbols or [s for s in available if s in allowed]
    if start is None:return pd.DataFrame()
    data=store.get_price_data(names,start,end)
    data=data.rename(columns={'tic':'symbol','datadate':'date','prcod':'open','prchd':'high','prcld':'low','prccd':'close','cshtrd':'volume'})
    data['date']=pd.to_datetime(data.date,utc=True).dt.tz_localize(None)
    return data


def backtest(frame,registry):
    """Convert original environment holdings to the official StrategyResult API."""
    import pandas as pd
    from stable_baselines3 import SAC
    saved=policy_files()
    from .state_io import read_json
    identity=read_json(saved/'dataset.json')
    if identity.get('champion_file'):
        from .platform.sac_champion import load_spec
        registry.close()
        champion=load_spec(identity['champion_file'])
        from .expert_registry_native import ExpertRegistry
        registry=ExpertRegistry(champion=champion)
        champion_ids=champion['identity']['champion_experts']
    else:champion_ids=None
    env=training_environment(frame,registry,training=False,champion_ids=champion_ids)
    try:
        if identity.get('currency')!=env.currency or identity.get('symbols')!=env.symbols:raise ValueError('저장된 정책과 통화·종목 구성이 다릅니다.')
        model=SAC.load(saved/'sac.zip',env=env)
        from finrl.agents.stablebaselines3.models import DRLAgent
        _,weights=DRLAgent.DRL_prediction(model=model,environment=env)
        result=finrlx('strategies.base_strategy').StrategyResult('Official SAC',weights)
        module=finrlx('backtest.backtest_engine')
        config=module.BacktestConfig(str(frame.date.min().date()),str(frame.date.max().date()))
        selected=env.unwrapped.df.rename(columns={'tic':'symbol'})
        prices_wide=selected.pivot(index='date',columns='symbol',values='close')
        evaluated=module.BacktestEngine(config).run_backtest(result.strategy_name,prices_wide,result.weights)
        return evaluated
    finally:env.close()


def policy_files():
    """Select an existing native SB3 revision without modifying its weights."""
    from .state_io import read_json
    root=ROOT/'runtime/official'
    selection=read_json(root/'active-checkpoint.json')
    if not selection:return root
    path=(root/selection['path']).resolve()
    if not path.is_relative_to(root.resolve()) or path.name!='sac.zip':
        raise ValueError('기존 SAC 체크포인트 경로가 유효하지 않습니다.')
    return path.parent
