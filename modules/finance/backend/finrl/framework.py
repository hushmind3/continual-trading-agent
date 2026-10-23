"""Primary FinRL/SB3 environments, learners and saved policies."""
import importlib.util
import sys
import threading
from pathlib import Path

from .. import ROOT
CASH_ENVIRONMENT='stockrl.finrl.policy_learning.market_environment.MarketLearningEnv'
_module_lock=threading.RLock()


def cash_environment(frame,registry,symbols,champion_ids=None,structure_only=False):
    """Learn against the same sparse-price, whole-share ledger used in operation."""
    from .policy_learning.market_environment import MarketLearningEnv
    from ..expert_observation import ExpertObservation
    currency='KRW' if any(str(s).endswith(('.KS','.KQ')) for s in symbols) else 'USD'
    raw=MarketLearningEnv(frame,symbols,currency,start_index=frame.attrs.get('initial_time_index'),continuous=frame.attrs.get('continuous',False))
    wrapped=ExpertObservation(raw,registry,frame,symbols,champion_ids=champion_ids,structure_only=structure_only)
    wrapped.source_environment=CASH_ENVIRONMENT;wrapped.currency=currency
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


def learning_frame(frame,training=True,include_latest=False,since=None):
    """Keep evaluation chronological; continuation consumes newly completed bars."""
    import pandas as pd
    dates=pd.to_datetime(frame.date)
    unique=sorted(dates.dropna().unique())
    if len(unique)<2:raise ValueError('학습·평가 구간에 서로 다른 시각의 실제 가격이 부족합니다.')
    trade_date=dates.max()+pd.Timedelta(nanoseconds=1)
    start=trade_date-pd.Timedelta(days=1095 if training else 365)
    boundary=trade_date-pd.Timedelta(days=365)
    if dates.min()>=boundary:
        boundary=pd.Timestamp(unique[max(1,min(len(unique)-1,int(len(unique)*.8)))])
    end=boundary if training and not include_latest else trade_date
    if not training:start=boundary
    initial_index=None
    if training and include_latest and since is not None:
        from .policy_learning.market_environment import MarketLearningEnv
        eligible=pd.DatetimeIndex(sorted(dates[(dates>=start)&(dates<end)].unique()))
        if len(eligible)<2:raise ValueError('이어 학습 구간에 서로 다른 시각의 실제 가격이 부족합니다.')
        consumed=pd.Timestamp(since)
        if pd.isna(consumed):raise ValueError('저장된 학습 완료 시각이 유효하지 않습니다.')
        if consumed>dates.max():raise ValueError('저장된 학습 완료 시각보다 최신 입력의 시각이 오래됐습니다.')
        next_index=min(int(eligible.searchsorted(consumed,side='right')),len(eligible)-1)
        context_index=max(0,next_index-MarketLearningEnv.WARMUP_BARS)
        start=pd.Timestamp(eligible[context_index])
        initial_index=max(0,next_index-context_index-1)
    prepared=frame[(dates>=start)&(dates<end)].sort_values(['date','symbol']).reset_index(drop=True)
    prepared.attrs.update(frame.attrs)
    prepared.attrs['continuous']=bool(training and include_latest)
    if initial_index is not None:prepared.attrs['initial_time_index']=initial_index
    if prepared.date.nunique()<2:raise ValueError('학습·평가 구간에 서로 다른 시각의 실제 가격이 부족합니다.')
    return prepared


def training_environment(frame,registry,training=True,champion_ids=None,include_latest=False,since=None):
    prepared=learning_frame(frame,training,include_latest,since)
    active=list(registry.catalog().get('active',[])) if champion_ids is None else list(champion_ids)
    wrapped=cash_environment(prepared,registry,sorted(frame.symbol.unique()),active)
    wrapped.frame=frame
    return wrapped


def policy_timeframe(identity):
    value=identity.get('timeframe') or identity.get('training_input',{}).get('timeframe') or '1d'
    if value not in ('1d','1m'):raise ValueError('저장 정책의 학습 가격 주기를 확인할 수 없습니다.')
    return value


def champion_structure_environment(currency,symbols,registry,champion_ids):
    """Inspect the selected cash-enabled spaces without market or Expert inference."""
    import pandas as pd
    count=len(symbols);stamp=pd.Timestamp('2000-01-01')
    frame=pd.DataFrame({'date':[stamp]*count+[stamp+pd.Timedelta(days=1)]*count,'symbol':symbols*2,'open':[1.]*(count*2),'close':[1.]*(count*2),'high':[1.]*(count*2),'low':[1.]*(count*2),'volume':[0.]*(count*2)})
    wrapped=cash_environment(frame,registry,symbols,champion_ids,structure_only=True)
    wrapped.currency=currency
    return wrapped


def train(frame,registry,resume=False,output=None,champion_path=None,champion_output=None,algorithm='sac',total_timesteps=None,champion=None,source_checkpoint=None):
    from time import perf_counter
    started=perf_counter()
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
    if champion and champion['identity']['environment']!=CASH_ENVIRONMENT:raise ValueError('현재 학습 환경의 Champion으로 새로 생성하세요.')
    saved=policy_files(currency,source_checkpoint)
    if resume and read_json(saved/'dataset.json').get('environment')!=CASH_ENVIRONMENT:raise ValueError('구형 환경의 정책은 실행하지 않습니다. 현금 정책을 새로 학습하세요.')
    if resume and champion_ids is None:champion_ids=read_json(saved/'dataset.json').get('champion_experts')
    champion_ids=list(registry.catalog().get('active',[])) if champion_ids is None else champion_ids
    consumed=read_json(saved/'dataset.json').get('training_input',{}).get('consumed_end') if resume else None
    env=training_environment(frame,registry,champion_ids=champion_ids,include_latest=resume,since=consumed)
    root=Path(output) if output is not None else ROOT/'runtime/finance/policy_learning'
    if not root.resolve().is_relative_to((ROOT/'runtime/finance/policy_learning').resolve()):raise ValueError('정책 출력은 기존 runtime/finance/policy_learning 내부에 저장합니다.')
    root.mkdir(parents=True,exist_ok=True)
    saved=policy_files(env.currency,source_checkpoint)
    identity={'currency':env.currency,'symbols':env.symbols,'algorithm':algorithm,'sac_example':parameters,'environment':CASH_ENVIRONMENT,'rolling_days':[1095,365]}
    from ..platform.sac_champion import _candidate_identity,_policy_kwargs,_original_report
    base_dim=int(__import__('numpy').prod(env.unwrapped.observation_space.shape))
    if algorithm=='sac' or champion:identity.update(_candidate_identity(env.currency,env.symbols,champion_ids,base_dim,CASH_ENVIRONMENT,algorithm))
    else:identity.update(champion_experts=champion_ids,base_observation_dim=base_dim,account_feature_size=16,observation_contract='expert-observation-v1')
    if champion:
        identity.update(champion['identity'])
        if champion_output:identity['champion_file']=str(Path(champion_output))
    identity['timeframe']=frame.attrs.get('timeframe','1d')
    try:
        if resume:
            previous=read_json(saved/'dataset.json');previous.setdefault('algorithm','sac')
            previous.setdefault('timeframe',policy_timeframe(previous))
            if any(previous.get(key)!=value for key,value in identity.items() if key!='champion_file'):raise ValueError('저장된 정책과 알고리즘·통화·종목·Expert 구성이 다릅니다. 새 학습으로 시작하세요.')
            identity={**previous,**identity}
        from hashlib import sha256
        import pandas as pd
        identity['training_input']={'fingerprint':sha256(pd.util.hash_pandas_object(frame,index=True).values.tobytes()).hexdigest(),'observations':len(frame),'end':str(frame.date.max()),'timeframe':identity['timeframe'],'source':frame.attrs.get('source','unknown')}
        agent=DRLAgent(env=env)
        print('FinRL DRLAgent ·',algorithm.upper(),parameters,'단계:',steps,flush=True)
        if champion:
            checkpoint=Path(source_checkpoint) if resume and source_checkpoint else Path(champion['checkpoint'])
            if not checkpoint.is_absolute():checkpoint=ROOT/'runtime/finance/policy_learning'/checkpoint
            if (checkpoint.parent/'replay.pkl').is_file() and policy_timeframe(read_json(checkpoint.parent/'dataset.json'))!=identity['timeframe']:
                raise ValueError('저장된 Replay와 입력 가격 주기가 다릅니다. 해당 주기의 새 정책을 생성하세요.')
            model=system.model(checkpoint,algorithm,env)
            if hasattr(model,'load_replay_buffer') and (checkpoint.parent/'replay.pkl').is_file():model.load_replay_buffer(checkpoint.parent/'replay.pkl')
            from finrl.agents.stablebaselines3.models import TensorboardCallback
            model=model.learn(total_timesteps=steps,tb_log_name=algorithm,callback=TensorboardCallback(),reset_num_timesteps=False)
        elif resume:
            model=system.model(policy_checkpoint(saved),algorithm,env)
            if hasattr(model,'load_replay_buffer'):model.load_replay_buffer(saved/'replay.pkl')
            from finrl.agents.stablebaselines3.models import TensorboardCallback
            model=model.learn(total_timesteps=steps,tb_log_name=algorithm,callback=TensorboardCallback(),reset_num_timesteps=False)
        else:
            roles={key:registry.catalog()['experts'][key]['role'] for key in champion_ids}
            kwargs={'policy_kwargs':_policy_kwargs(identity,roles,_original_report())} if algorithm=='sac' else {}
            model=agent.get_model(algorithm,model_kwargs=dict(parameters),**kwargs)
            model=agent.train_model(model=model,tb_log_name=algorithm,total_timesteps=steps)
        native=env.unwrapped
        identity['training_input'].update(training_start=str(native._sorted_times[native._start_index]),
            training_end=str(native._sorted_times[-1]),consumed_end=str(native.consumed_until) if native.consumed_until is not None else None,
            transitions=int(native.transition_count))
        model.save(root/algorithm)
        if hasattr(model,'save_replay_buffer'):model.save_replay_buffer(root/'replay.pkl')
        identity['training_input']['elapsed_seconds']=perf_counter()-started
        identity['training_input']['requested_timesteps']=steps
        atomic_json(identity,root/'dataset.json')
        if champion and champion_output:
            from ..platform.sac_champion import save_trained_champion
            save_trained_champion(champion_path,model,Path(champion_output),root,spec={**champion,'identity':dict(identity)})
        print('학습 완료:',model.num_timesteps,'관측,',getattr(model,'_n_updates',None),'업데이트',flush=True)
    finally:env.close()
    return model






def policy_files(currency=None,checkpoint=None):
    """Select an existing native SB3 revision without modifying its weights."""
    from ..state_io import read_json
    root=ROOT/'runtime/finance/policy_learning'
    if checkpoint is not None:
        path=Path(checkpoint).expanduser();path=(path if path.is_absolute() else root/path).resolve()
        if not path.is_relative_to(root.resolve()) or path.suffix!='.zip' or not path.is_file():raise ValueError('운영 폴더의 실제 정책 ZIP을 선택하세요.')
        identity=read_json(path.parent/'dataset.json')
        if currency and identity.get('currency')!=currency:raise ValueError('이어 학습 정책의 통화가 다릅니다.')
        if policy_checkpoint(path.parent)!=path:raise ValueError('이어 학습 정책 경로와 알고리즘이 다릅니다.')
        return path.parent
    selected=read_json(ROOT/'runtime/finance/operation_control/policies.json').get(currency) if currency else None
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
