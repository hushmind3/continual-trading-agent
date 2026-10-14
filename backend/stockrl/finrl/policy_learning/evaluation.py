"""Chronological paper evaluation of saved policies; never touches live account state."""
from pathlib import Path
import numpy as np
from stockrl import ROOT
from stockrl.state_io import read_json,atomic_json


def evaluate_pair(checkpoint,baseline_checkpoint):
    from stockrl.finrl.framework import policy_files,training_environment,CASH_ENVIRONMENT,policy_timeframe
    from stockrl.finrl.price_data.operations import prices
    from stockrl.expert_registry_native import ExpertRegistry
    from stockrl.platform.sac_champion import load_spec
    from stockrl.platform.system_operations import system
    paths=[]
    for value in (baseline_checkpoint,checkpoint):
        path=Path(value).expanduser()
        if not path.is_absolute():path=(ROOT/path) if path.parts[:2]==('runtime','official') else (ROOT/'runtime/official'/path)
        paths.append(path.resolve())
    identities=[read_json(policy_files(checkpoint=path)/'dataset.json') for path in paths]
    for key in ('currency','symbols','environment'):
        if identities[0].get(key)!=identities[1].get(key):raise ValueError('비교 정책의 '+key+' 구성이 다릅니다.')
    if identities[1]['environment']!=CASH_ENVIRONMENT:raise ValueError('현재 원장 환경의 정책을 선택하세요.')
    if policy_timeframe(identities[0])!=policy_timeframe(identities[1]):raise ValueError('비교 정책의 가격 주기가 다릅니다.')
    frame=prices(identities[1]['currency'],identities[1]['symbols'],timeframe=policy_timeframe(identities[1]))
    reports=[]
    try:
        for path,identity in zip(paths,identities):
            spec=load_spec(identity['champion_file']) if identity.get('champion_file') else None
            registry=ExpertRegistry(champion=spec);env=None
            try:
                env=training_environment(frame,registry,training=False,champion_ids=identity.get('champion_experts',[]))
                model=system.model(path.resolve(),identity.get('algorithm','sac'),env)
                observation,_=env.reset();raw=env.unwrapped;initial=raw._initial_amount
                curve=[{'date':raw._info['end_time'],'equity':initial}];steps=0
                while True:
                    action,_=model.predict(observation,deterministic=True)
                    observation,reward,done,truncated,info=env.step(action);steps+=1
                    curve.append({'date':info['end_time'],'equity':info['portfolio_value'],'reward':float(reward),'fills':len(info['fills'])})
                    if steps%64==0:print('평가',path.parent.name,steps,'단계',flush=True)
                    if done or truncated:break
                book=raw.account.snapshot()['books'][identity['currency']]
                equity=np.array([point['equity'] for point in curve]);peaks=np.maximum.accumulate(equity)
                reports.append({'checkpoint':str(path),'device':str(model.device),'num_timesteps':int(model.num_timesteps),
                    'updates':int(getattr(model,'_n_updates',0)),'steps':steps,'start':curve[0]['date'],'end':curve[-1]['date'],
                    'initial_equity':initial,'final_equity':float(equity[-1]),'return_pct':float((equity[-1]/initial-1)*100),
                    'max_drawdown_pct':float(np.max(1-equity/peaks)*100),'fees':book['fees'],'fills':book['trade_count'],'curve':curve})
            finally:
                if env is not None:env.close()
                registry.close(cleanup=True)
        report={'kind':'chronological_paper_comparison','currency':identities[1]['currency'],'symbols':identities[1]['symbols'],
            'source':frame.attrs.get('source'),'timeframe':frame.attrs.get('timeframe'),'baseline':reports[0],'candidate':reports[1],
            'return_difference_percentage_points':reports[1]['return_pct']-reports[0]['return_pct'],
            'limit':'기록된 과거 완료 봉의 비용 반영 가상평가입니다. 실거래·미래 수익을 확인한 결과가 아닙니다.'}
        destination=Path(identities[1].get('champion_file',checkpoint)).with_suffix('.evaluation.json')
        atomic_json(report,destination)
        return {'path':str(destination),**{key:report[key] for key in ('currency','return_difference_percentage_points')},
            'baseline_return_pct':reports[0]['return_pct'],'candidate_return_pct':reports[1]['return_pct']}
    finally:system.close_models()
