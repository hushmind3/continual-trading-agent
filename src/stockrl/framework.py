"""Official framework entrypoints; no policy, loss, optimizer or replay implementation."""
import importlib
import importlib.util
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CASH_ENVIRONMENT='finrl.meta.env_portfolio_optimization.env_portfolio_optimization.PortfolioOptimizationEnv'


def cash_environment(frame,registry,symbols,champion_ids=None,structure_only=False):
    """Adapt the official cash-enabled Gym environment to Gymnasium; no trading rules."""
    from shimmy import GymV21CompatibilityV0
    from .expert_observation import ExpertObservation
    raw=finrl_file('meta/env_portfolio_optimization/env_portfolio_optimization.py').PortfolioOptimizationEnv(
        df=frame.rename(columns={'symbol':'tic'}).copy(),initial_amount=1000000,
        cwd=str(ROOT/'runtime/official'))
    wrapped=ExpertObservation(GymV21CompatibilityV0(env=raw),registry,frame,list(raw._tic_list),
        champion_ids=champion_ids,structure_only=structure_only)
    wrapped.source_environment=CASH_ENVIRONMENT
    wrapped.currency='KRW' if any(str(s).endswith(('.KS','.KQ')) for s in symbols) else 'USD'
    return wrapped


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
    import pandas as pd
    example=finrlx('strategies.rl_model');trade_date=frame.date.max()+pd.Timedelta(days=1)
    prepared=(example.prepare_rolling_train if training else example.prepare_rolling_test)(
        frame.rename(columns={'symbol':'tic'}),'date',pd.Timedelta(days=365),pd.Timedelta(days=1095),trade_date)
    prepared=prepared.rename(columns={'tic':'symbol'})
    if prepared.empty:raise ValueError('공식 rolling 구간에 PortfolioOptimizationEnv 가격 입력이 없습니다.')
    active=list(registry.catalog().get('active',[])) if champion_ids is None else list(champion_ids)
    wrapped=cash_environment(prepared,registry,sorted(prepared.symbol.unique()),active)
    wrapped.frame=frame
    return wrapped


def champion_structure_environment(currency,symbols,registry,champion_ids):
    """Inspect the same official cash-enabled spaces without market or Expert inference."""
    import pandas as pd
    count=len(symbols);stamp=pd.Timestamp('2000-01-01')
    frame=pd.DataFrame({'date':[stamp]*count,'symbol':symbols,'close':[1.]*count,'high':[1.]*count,'low':[1.]*count})
    wrapped=cash_environment(frame,registry,symbols,champion_ids,structure_only=True)
    wrapped.currency=currency
    return wrapped


def train(frame,registry,resume=False,output=None,champion_path=None,champion_output=None):
    from stable_baselines3 import SAC
    from finrl.agents.stablebaselines3.models import DRLAgent
    from .platform.sac_champion import load_spec
    champion = load_spec(champion_path) if champion_path else None
    champion_ids = champion.get('identity',{}).get('champion_experts') if champion else None
    from .state_io import read_json,atomic_json
    currency='KRW' if any(str(s).endswith(('.KS','.KQ')) for s in frame.symbol.unique()) else 'USD'
    if champion and champion['identity']['environment']!=CASH_ENVIRONMENT:raise ValueError('PortfolioOptimizationEnv Champion으로 새로 생성하세요.')
    if resume and read_json(policy_files(currency)/'dataset.json').get('environment')!=CASH_ENVIRONMENT:raise ValueError('구형 환경의 정책은 실행하지 않습니다. 현금 정책을 새로 학습하세요.')
    champion_ids=list(registry.catalog().get('active',[])) if champion_ids is None else champion_ids
    env=training_environment(frame,registry,champion_ids=champion_ids)
    example,parameters,steps=sac_example()
    root=Path(output) if output is not None else ROOT/'runtime/official'
    if not root.resolve().is_relative_to((ROOT/'runtime/official').resolve()):raise ValueError('정책 출력은 기존 runtime/official 내부에 저장합니다.')
    root.mkdir(parents=True,exist_ok=True)
    from .state_io import read_json,atomic_json
    saved=policy_files(env.currency)
    identity={'currency':env.currency,'symbols':env.symbols,'sac_example':parameters,'environment':CASH_ENVIRONMENT,'rolling_days':[1095,365]}
    from .platform.sac_champion import _candidate_identity,_policy_kwargs,_original_report
    identity.update(_candidate_identity(env.currency,env.symbols,champion_ids,int(__import__('numpy').prod(env.unwrapped.observation_space.shape)),CASH_ENVIRONMENT))
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
        else:
            roles={key:registry.catalog()['experts'][key]['role'] for key in champion_ids}
            model=agent.get_model('sac',model_kwargs=dict(parameters),policy_kwargs=_policy_kwargs(identity,roles,_original_report()))
            model=agent.train_model(model=model,tb_log_name='sac',total_timesteps=steps)
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
    allowed=set(available) if currency is None else {i['symbol'] for i in market['instruments'] if i.get('market') in (('KRX','KOSDAQ') if currency=='KRW' else ('US','NASDAQ','NYSE','NYSEARCA','AMEX')) and i.get('asset_class') in ('equity','etf')}
    names=symbols or [s for s in available if s in allowed]
    if start is None:return pd.DataFrame()
    data=store.get_price_data(names,start,end)
    data=data.rename(columns={'tic':'symbol','datadate':'date','prcod':'open','prchd':'high','prcld':'low','prccd':'close','cshtrd':'volume'})
    data['date']=pd.to_datetime(data.date,utc=True).dt.tz_localize(None)
    return data


def backtest(frame,registry,currency=None):
    """Convert original environment holdings to the official StrategyResult API."""
    import pandas as pd
    from stable_baselines3 import SAC
    saved=policy_files(currency)
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
    if identity.get('environment')!=CASH_ENVIRONMENT:raise ValueError('구형 환경 정책은 백테스트하지 않습니다.')
    env=training_environment(frame,registry,training=False,champion_ids=identity.get('champion_experts',[]))
    try:
        if identity.get('currency')!=env.currency or identity.get('symbols')!=env.symbols:raise ValueError('저장된 정책과 통화·종목 구성이 다릅니다.')
        model=SAC.load(saved/'sac.zip',env=env)
        from finrl.agents.stablebaselines3.models import DRLAgent
        observation,_=env.reset();raw=env.unwrapped.gym_env;rows=[]
        while not raw._terminal:
            action,_=model.predict(observation,deterministic=True)
            observation,_,terminal,truncated,_=env.step(action)
            allocation=raw._actions_memory[-1]
            rows.append({'date':raw._info['end_time'],**dict(zip(env.symbols,allocation[1:])), 'CASH':float(allocation[0])})
            if terminal or truncated:break
        weights=pd.DataFrame(rows).set_index('date')
        result=finrlx('strategies.base_strategy').StrategyResult('Official SAC',weights)
        module=finrlx('backtest.backtest_engine')
        config=module.BacktestConfig(str(frame.date.min().date()),str(frame.date.max().date()))
        selected=frame[frame.date.isin(env.unwrapped.gym_env._sorted_times)]
        prices_wide=selected.pivot(index='date',columns='symbol',values='close')
        prices_wide['CASH']=1.
        evaluated=module.BacktestEngine(config).run_backtest(result.strategy_name,prices_wide,result.weights)
        return evaluated
    finally:env.close()


def policy_files(currency=None):
    """Select an existing native SB3 revision without modifying its weights."""
    from .state_io import read_json
    root=ROOT/'runtime/official'
    selected=read_json(ROOT/'runtime/operations/policies.json').get(currency) if currency else None
    selection={'path':selected} if selected else read_json(root/'active-checkpoint.json')
    if not selection:return root
    path=(root/selection['path']).resolve()
    if not path.is_relative_to(root.resolve()) or path.name!='sac.zip':
        raise ValueError('기존 SAC 체크포인트 경로가 유효하지 않습니다.')
    return path.parent
