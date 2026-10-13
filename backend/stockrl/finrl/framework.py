"""Primary FinRL/SB3 environments, learners and saved policies."""
import importlib.util
import sys
import threading
from pathlib import Path

from .. import ROOT
CASH_ENVIRONMENT='finrl.meta.env_portfolio_optimization.env_portfolio_optimization.PortfolioOptimizationEnv'
_module_lock=threading.RLock()


def cash_environment(frame,registry,symbols,champion_ids=None,structure_only=False):
    """Adapt the official cash-enabled Gym environment to Gymnasium; no trading rules."""
    from shimmy import GymV21CompatibilityV0
    from ..expert_observation import ExpertObservation
    raw=finrl_file('meta/env_portfolio_optimization/env_portfolio_optimization.py').PortfolioOptimizationEnv(
        df=frame.rename(columns={'symbol':'tic'}).copy(),initial_amount=1000000,
        cwd=str(ROOT/'runtime/official'))
    wrapped=ExpertObservation(GymV21CompatibilityV0(env=raw),registry,frame,list(raw._tic_list),
        champion_ids=champion_ids,structure_only=structure_only)
    wrapped.source_environment=CASH_ENVIRONMENT
    wrapped.currency='KRW' if any(str(s).endswith(('.KS','.KQ')) for s in symbols) else 'USD'
    return wrapped




def finrl_file(relative):
    # The upstream package __init__ eagerly imports optional brokers/agents.
    # Import the chosen official module file without rewriting its source.
    package=importlib.util.find_spec('finrl')
    path=Path(package.origin).parent/relative
    name='official_finrl_'+relative.replace('/','_').removesuffix('.py')
    with _module_lock:
        if name in sys.modules:return sys.modules[name]
        spec=importlib.util.spec_from_file_location(name,path)
        module=importlib.util.module_from_spec(spec);sys.modules[name]=module
        try:spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(name,None);raise
        return module


def sac_example(algorithm='sac'):
    import inspect
    from finrl.agents.stablebaselines3.models import DRLAgent,MODEL_KWARGS,MODELS
    if algorithm not in MODELS:raise ValueError('FinRL에서 지원하지 않는 알고리즘입니다: '+algorithm)
    function=DRLAgent.train_model
    steps=inspect.signature(function).parameters['total_timesteps'].default
    return function,dict(MODEL_KWARGS[algorithm]),steps


def validate_price_panel(frame,symbols):
    if frame.empty:raise ValueError('공식 환경에 전달할 실제 가격 구간이 비어 있습니다.')
    counts=frame.groupby('date').symbol.agg(['size','nunique'])
    invalid=counts[(counts['size']!=len(symbols))|(counts['nunique']!=len(symbols))]
    if not invalid.empty:
        stamp=invalid.index[0];present=set(frame.loc[frame.date==stamp,'symbol'])
        missing=sorted(set(symbols)-present)
        raise ValueError(f'PortfolioOptimizationEnv 가격 행렬이 불완전한 날짜 {len(invalid)}개: {stamp}; 누락 종목 {missing}; 행 {int(invalid.iloc[0]["size"])} / 필요 {len(symbols)}. 실제 가격을 준비하거나 학습 종목을 직접 선택하세요.')


def training_environment(frame,registry,training=True,champion_ids=None):
    import pandas as pd
    from finrl.meta.preprocessor.preprocessors import data_split
    trade_date=frame.date.max()+pd.Timedelta(days=1)
    start=trade_date-pd.Timedelta(days=1095 if training else 365)
    end=trade_date-pd.Timedelta(days=365) if training else trade_date
    prepared=data_split(frame.rename(columns={'symbol':'tic'}),start,end)
    prepared=prepared.rename(columns={'tic':'symbol'})
    if prepared.empty:raise ValueError('공식 rolling 구간에 PortfolioOptimizationEnv 가격 입력이 없습니다.')
    validate_price_panel(prepared,sorted(frame.symbol.unique()))
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


def train(frame,registry,resume=False,output=None,champion_path=None,champion_output=None,algorithm='sac',total_timesteps=None,champion=None):
    from finrl.agents.stablebaselines3.models import DRLAgent
    from ..platform.system_operations import system
    example,parameters,steps=sac_example(algorithm)
    steps=steps if total_timesteps is None else int(total_timesteps)
    if steps<1:raise ValueError('학습 단계는 1 이상이어야 합니다.')
    from ..platform.sac_champion import load_spec
    if champion is None and champion_path:champion=load_spec(champion_path)
    if champion and champion['identity']['algorithm']!=algorithm:raise ValueError('선택한 알고리즘과 Champion의 알고리즘이 다릅니다.')
    champion_ids = champion.get('identity',{}).get('champion_experts') if champion else None
    from ..state_io import read_json,atomic_json
    currency='KRW' if any(str(s).endswith(('.KS','.KQ')) for s in frame.symbol.unique()) else 'USD'
    if champion and champion['identity']['environment']!=CASH_ENVIRONMENT:raise ValueError('PortfolioOptimizationEnv Champion으로 새로 생성하세요.')
    if resume and read_json(policy_files(currency)/'dataset.json').get('environment')!=CASH_ENVIRONMENT:raise ValueError('구형 환경의 정책은 실행하지 않습니다. 현금 정책을 새로 학습하세요.')
    champion_ids=list(registry.catalog().get('active',[])) if champion_ids is None else champion_ids
    env=training_environment(frame,registry,champion_ids=champion_ids)
    root=Path(output) if output is not None else ROOT/'runtime/official'
    if not root.resolve().is_relative_to((ROOT/'runtime/official').resolve()):raise ValueError('정책 출력은 기존 runtime/official 내부에 저장합니다.')
    root.mkdir(parents=True,exist_ok=True)
    saved=policy_files(env.currency)
    identity={'currency':env.currency,'symbols':env.symbols,'algorithm':algorithm,'sac_example':parameters,'environment':CASH_ENVIRONMENT,'rolling_days':[1095,365]}
    from ..platform.sac_champion import _candidate_identity,_policy_kwargs,_original_report
    base_dim=int(__import__('numpy').prod(env.unwrapped.observation_space.shape))
    if algorithm=='sac' or champion:identity.update(_candidate_identity(env.currency,env.symbols,champion_ids,base_dim,CASH_ENVIRONMENT,algorithm))
    else:identity.update(champion_experts=champion_ids,base_observation_dim=base_dim,account_feature_size=16,observation_contract='expert-observation-v1')
    if champion:
        identity.update(champion['identity'])
        if champion_output:identity['champion_file']=str(Path(champion_output))
    try:
        if resume:
            previous=read_json(saved/'dataset.json');previous.setdefault('algorithm','sac')
            if previous!=identity:raise ValueError('저장된 정책과 알고리즘·통화·종목·Expert 구성이 다릅니다. 새 학습으로 시작하세요.')
        agent=DRLAgent(env=env)
        print('FinRL DRLAgent ·',algorithm.upper(),parameters,'단계:',steps,flush=True)
        if champion:
            checkpoint=Path(champion['checkpoint'])
            if not checkpoint.is_absolute():checkpoint=ROOT/'runtime/official'/checkpoint
            model=system.model(checkpoint,algorithm,env)
            if hasattr(model,'load_replay_buffer') and (checkpoint.parent/'replay.pkl').is_file():model.load_replay_buffer(checkpoint.parent/'replay.pkl')
            model=agent.train_model(model=model,tb_log_name=algorithm,total_timesteps=steps)
        elif resume:
            model=system.model(policy_checkpoint(saved),algorithm,env)
            if hasattr(model,'load_replay_buffer'):model.load_replay_buffer(saved/'replay.pkl')
            model=agent.train_model(model=model,tb_log_name=algorithm,total_timesteps=steps)
        else:
            roles={key:registry.catalog()['experts'][key]['role'] for key in champion_ids}
            kwargs={'policy_kwargs':_policy_kwargs(identity,roles,_original_report())} if algorithm=='sac' else {}
            model=agent.get_model(algorithm,model_kwargs=dict(parameters),**kwargs)
            model=agent.train_model(model=model,tb_log_name=algorithm,total_timesteps=steps)
        model.save(root/algorithm)
        if hasattr(model,'save_replay_buffer'):model.save_replay_buffer(root/'replay.pkl')
        atomic_json(identity,root/'dataset.json')
        if champion and champion_output:
            from ..platform.sac_champion import save_trained_champion
            save_trained_champion(champion_path,model,Path(champion_output),root,spec=champion)
        print('학습 완료:',model.num_timesteps,'관측,',getattr(model,'_n_updates',None),'업데이트',flush=True)
    finally:env.close()
    return model






def policy_files(currency=None):
    """Select an existing native SB3 revision without modifying its weights."""
    from ..state_io import read_json
    root=ROOT/'runtime/official'
    selected=read_json(ROOT/'runtime/operations/policies.json').get(currency) if currency else None
    selection={'path':selected} if selected else read_json(root/'active-checkpoint.json')
    if not selection:return root
    path=(root/selection['path']).resolve()
    from finrl.agents.stablebaselines3.models import MODELS
    if not path.is_relative_to(root.resolve()) or path.suffix!='.zip' or path.stem not in MODELS:
        raise ValueError('기존 SAC 체크포인트 경로가 유효하지 않습니다.')
    return path.parent


def policy_checkpoint(folder):
    from ..state_io import read_json
    from finrl.agents.stablebaselines3.models import MODELS
    algorithm=read_json(Path(folder)/'dataset.json').get('algorithm','sac')
    if algorithm not in MODELS:raise ValueError('저장된 정책의 FinRL 알고리즘을 확인할 수 없습니다.')
    return Path(folder)/(algorithm+'.zip')
