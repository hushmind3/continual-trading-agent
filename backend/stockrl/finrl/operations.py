"""FinRL data, algorithm and evaluation operations."""
import ast
import json
import subprocess
import sys
from pathlib import Path
from functools import lru_cache
from urllib.parse import quote
from .. import ROOT
from .framework import finrl_file
from ..state_io import atomic_json,read_json

ACTIONS={
    'stock_data':('FinRL 데이터 준비', 'finrl', 'FinRL:meta.preprocessor.preprocessors', 'YahooDownloader → FeatureEngineer → data_split', []),
    'stock_train':('FinRL 모델별 학습', 'finrl', 'FinRL:agents.stablebaselines3.models', 'DRLAgent.get_model → train_model', []),
    'stock_backtest':('FinRL 모델·MVO·DJIA 백테스트', 'finrl', 'FinRL:agents.stablebaselines3.models', 'DRLAgent.DRL_prediction · 공식 MVO/DJIA 예제', []),
    'finrl_workflow':('FinRL 원형 학습·평가·모의매매', 'workflows', 'FinRL:main', 'main', ['mode']),
    'yahoo':('FinRL Yahoo 가격 수집', 'markets', 'FinRL:meta.preprocessor.yahoodownloader', 'YahooDownloader.fetch_data', ['symbols', 'start_date', 'end_date']),
    'features':('FinRL 기술지표·전처리', 'markets', 'FinRL:meta.preprocessor.preprocessors', 'FeatureEngineer.preprocess_data', ['currency', 'symbols']),
    'data_split':('FinRL 기간 분할', 'markets', 'FinRL:meta.preprocessor.preprocessors', 'data_split', ['currency', 'symbols', 'start_date', 'end_date']),
    'finrl_stats':('FinRL 백테스트 성과', 'portfolio', 'FinRL:plot', 'backtest_stats', ['currency']),
}

def execute(action,parameters,output):
    from ..platform.framework_operations import serialize
    import pandas as pd
    if action not in ACTIONS:raise ValueError('등록된 FinRL 실행 기능이 아닙니다.')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if action in ('stock_data','stock_train','stock_backtest'):return stock_workflow(action,parameters,output)
    p={key:value for key,value in parameters.items() if value not in ('',None,[])}
    row=ACTIONS[action]
    if action=='finrl_workflow':
        mode=p.get('mode','train')
        if mode not in ('train','test','trade'):raise ValueError('공식 FinRL mode는 train / test / trade입니다.')
        print('FinRL 원형 main 실행 · 기본 Elegantrl PPO · 기존 SAC 운영 모델을 교체하지 않습니다.',flush=True)
        subprocess.run([sys.executable,'-m','finrl.main','--mode',mode],cwd=output,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        return {'action':action,'module':row[2],'function':row[3],'value':{'mode':mode,'output':str(output),'policy':'공식 main 기본 PPO'},'output':str(output.relative_to(ROOT))}
    module=finrl_file(row[2].split(':',1)[1].replace('.','/')+'.py')
    currency=p.get('currency','USD');symbols=p.get('symbols') or ([p['symbol']] if p.get('symbol') else None)
    if isinstance(symbols,str):symbols=[s.strip() for s in symbols.split(',') if s.strip()]
    print('공식 함수 실행:',row[2],row[3],flush=True)
    if action=='yahoo':value=module.YahooDownloader(start_date=p['start_date'],end_date=p['end_date'],ticker_list=symbols).fetch_data()
    elif action=='finrl_stats':
        file=ROOT/'runtime/official/backtests'/currency/'backtest.csv'
        if not file.is_file():raise ValueError(currency+' 실제 백테스트 결과가 없습니다.')
        data=pd.read_csv(file);data.columns=['date','account_value'] if len(data.columns)==2 else data.columns
        value=module.backtest_stats(data)
    else:
        from ..finrl_trading.data import prices
        frame=prices(currency,symbols)
        if frame.empty:raise ValueError('선택 종목의 실제 저장 가격이 없습니다.')
        if action=='features':value=module.FeatureEngineer().preprocess_data(frame.rename(columns={'symbol':'tic'}))
        elif action=='data_split':value=module.data_split(frame.rename(columns={'symbol':'tic'}),p['start_date'],p['end_date'])
        else:raise ValueError('FinRL 실행 어댑터가 없습니다.')
    if isinstance(value,pd.DataFrame):value.to_csv(output/'result.csv',index=False)
    result={'action':action,'module':row[2],'function':row[3],'output':str(output.relative_to(ROOT)),'value':serialize(value)}
    atomic_json(result,output/'result.json')
    print('공식 함수 실행 완료:',row[3],flush=True)
    return result


@lru_cache(maxsize=1)
def stock_sources():
    """Read the original examples at the installed FinRL revision without changing them."""
    import importlib.metadata
    import re
    import urllib.request
    installed=json.loads(importlib.metadata.distribution('finrl').read_text('direct_url.json') or '{}')
    revision=installed.get('vcs_info',{}).get('commit_id','')
    if not re.fullmatch('[0-9a-f]{40}',revision):raise ValueError('설치된 FinRL의 Git 커밋을 확인할 수 없습니다.')
    names=['FinRL_StockTrading_2026_1_data.py','FinRL_StockTrading_2026_2_train.py','FinRL_StockTrading_2026_3_Backtest.py']
    root=ROOT/'runtime/official/finrl-source'/revision/'examples'
    sources={}
    for name in names:
        path=root/name;url=f'https://raw.githubusercontent.com/AI4Finance-Foundation/FinRL/{revision}/examples/{name}'
        if not path.is_file():
            with urllib.request.urlopen(url,timeout=30) as response:source=response.read()
            root.mkdir(parents=True,exist_ok=True);path.write_bytes(source)
        sources[name]={'tree':ast.parse(path.read_text(encoding='utf8')),'path':path,
            'url':f'https://github.com/AI4Finance-Foundation/FinRL/blob/{revision}/examples/{name}'}
    return revision,sources

@lru_cache(maxsize=1)
def stock_settings():
    from finrl import config,config_tickers
    from finrl.agents.stablebaselines3.models import MODEL_KWARGS
    revision,sources=stock_sources();train=sources['FinRL_StockTrading_2026_2_train.py']['tree'];values={}
    for node in train.body:
        if not isinstance(node,ast.Assign):continue
        for target in node.targets:
            if not isinstance(target,ast.Name):continue
            try:values[target.id]=ast.literal_eval(node.value)
            except (ValueError,TypeError):pass
    algorithms=[key.removeprefix('if_using_') for key,value in values.items() if key.startswith('if_using_') and value is True]
    env_node=next(node.value for node in train.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='env_kwargs' for t in node.targets))
    env={ast.literal_eval(key):ast.literal_eval(value) for key,value in zip(env_node.keys,env_node.values) if isinstance(value,ast.Constant)}
    cost_node=next(node.value for node in train.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='buy_cost_list' for t in node.targets))
    cost=ast.literal_eval(cost_node.left.elts[0])
    steps=next(ast.literal_eval(keyword.value) for node in ast.walk(train) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='train_model' for keyword in node.keywords if keyword.arg=='total_timesteps')
    return {'revision':revision,'data_source':'Yahoo Finance','ticker_group':'DOW 30','tickers':config_tickers.DOW_30_TICKER,
        'train_start':config.TRAIN_START_DATE,'train_end':config.TRAIN_END_DATE,'trade_start':config.TRADE_START_DATE,'trade_end':config.TRADE_END_DATE,
        'indicators':config.INDICATORS,'use_vix':True,'use_turbulence':True,'environment':'finrl.meta.env_stock_trading.env_stocktrading.StockTradingEnv',
        'initial_amount':env['initial_amount'],'cost_pct':cost,'hmax':env['hmax'],'reward_scaling':env['reward_scaling'],
        'total_timesteps':steps,'algorithms':algorithms,'model_kwargs':{name:values.get(name.upper()+'_PARAMS',dict(MODEL_KWARGS[name])) for name in algorithms},
        'scripts':[{'name':name,'url':item['url']} for name,item in sources.items()]}

def stock_state():
    defaults=stock_settings();runs={key:[] for key in ('stock_data','stock_train','stock_backtest')}
    current=read_json(ROOT/'runtime/official/job.json')
    for path in sorted((ROOT/'runtime/official/framework-jobs').glob('*/result.json'),key=lambda p:p.stat().st_mtime,reverse=True):
        record=read_json(path);action=record.get('action')
        if action not in runs:continue
        status=record.get('status','complete' if not record.get('error') else 'failed')
        if current.get('id')==path.parent.name and current.get('status') in ('failed','stopped'):status=current['status']
        elif status=='running' and current.get('id')!=path.parent.name:status='interrupted'
        record.update(job_id=path.parent.name,status=status)
        if status in ('failed','stopped','interrupted'):
            for row in record.get('model_states',{}).values():
                if row.get('status') in ('running','queued'):row['status']='stopped' if status=='stopped' else 'interrupted'
        record['artifacts']=[{'name':name,'bytes':(path.parent/name).stat().st_size,
            'url':'/api?operation='+quote('framework/artifact/'+path.parent.name+'/'+name,safe='')} for name in record.get('files',[]) if (path.parent/name).is_file()]
        record.pop('executed_functions',None);runs[action].append(record)
    return {'defaults':defaults,'runs':runs}

def stock_workflow(action,parameters,output):
    """Port the original 2026 calls; keep each job's data/models/results isolated."""
    from ..platform.framework_operations import serialize
    import itertools
    import numpy as np
    import pandas as pd
    from contextlib import chdir
    from finrl.agents.stablebaselines3.models import DRLAgent
    from ..platform.system_operations import system
    from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv
    from finrl.meta.preprocessor.preprocessors import FeatureEngineer,data_split
    from finrl.meta.preprocessor.yahoodownloader import YahooDownloader
    defaults=stock_settings();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    record={'action':action,'module':ACTIONS[action][2],'function':ACTIONS[action][3],'status':'running',
        'output':str(output.relative_to(ROOT)),'files':[],'sources':defaults['scripts'],'revision':defaults['revision']}
    def save():atomic_json(record,output/'result.json')
    def existing(job_id,expected):
        import re
        if not re.fullmatch('[0-9a-f]{32}',str(job_id)):raise ValueError('선택한 원본 작업 ID가 필요합니다.')
        folder=ROOT/'runtime/official/framework-jobs'/job_id;data=read_json(folder/'result.json')
        if data.get('action')!=expected or data.get('status')!='complete':raise ValueError('선택한 작업의 완료된 실제 결과가 필요합니다.')
        return folder,data
    def frame(path):
        data=pd.read_csv(path);data=data.set_index(data.columns[0]);data.index.names=[''];return data
    def environment(data,settings):
        count=len(data.tic.unique())
        return {'hmax':defaults['hmax'],'initial_amount':settings['initial_amount'],'num_stock_shares':[0]*count,
            'buy_cost_pct':[settings['cost_pct']]*count,'sell_cost_pct':[settings['cost_pct']]*count,
            'state_space':1+2*count+len(defaults['indicators'])*count,'stock_dim':count,
            'tech_indicator_list':defaults['indicators'],'action_space':count,'reward_scaling':defaults['reward_scaling']}
    save()
    with chdir(output):
        if action=='stock_data':
            settings={key:parameters.get(key,defaults[key]) for key in ('tickers','train_start','train_end','trade_start','trade_end')}
            if isinstance(settings['tickers'],str):settings['tickers']=[s.strip() for s in settings['tickers'].split(',') if s.strip()]
            if not settings['tickers']:raise ValueError('YahooDownloader에 전달할 종목을 선택하세요.')
            for prefix in ('train','trade'):
                if pd.Timestamp(settings[prefix+'_start'])>=pd.Timestamp(settings[prefix+'_end']):raise ValueError('시작일은 종료일보다 앞서야 합니다.')
            record['settings']=settings;save()
            raw=YahooDownloader(start_date=settings['train_start'],end_date=settings['trade_end'],ticker_list=settings['tickers']).fetch_data()
            if raw.empty:raise ValueError('Yahoo Finance에서 실제 OHLCV를 받지 못했습니다.')
            processed=FeatureEngineer(use_technical_indicator=True,tech_indicator_list=defaults['indicators'],use_vix=True,use_turbulence=True,user_defined_feature=False).preprocess_data(raw)
            dates=list(pd.date_range(processed.date.min(),processed.date.max()).astype(str))
            full=pd.DataFrame(list(itertools.product(dates,processed.tic.unique().tolist())),columns=['date','tic']).merge(processed,on=['date','tic'],how='left')
            full=full[full.date.isin(processed.date)].sort_values(['date','tic']).fillna(0)
            train=data_split(full,settings['train_start'],settings['train_end']);trade=data_split(full,settings['trade_start'],settings['trade_end'])
            if train.empty or trade.empty:raise ValueError('선택한 기간의 실제 학습 또는 백테스트 데이터가 비어 있습니다.')
            train.to_csv(output/'train_data.csv');trade.to_csv(output/'trade_data.csv')
            record.update(files=['train_data.csv','trade_data.csv'],value={'raw_rows':len(raw),'train_rows':len(train),'trade_rows':len(trade),
                'stock_dimension':train.tic.nunique(),'columns':train.columns.tolist(),'train_preview':serialize(train.head(6)),'trade_preview':serialize(trade.head(6))})
        else:
            selected=parameters.get('algorithms',defaults['algorithms'])
            if not isinstance(selected,list) or not selected or any(name not in defaults['algorithms'] for name in selected):raise ValueError('공식 2026 예제의 학습 모델을 선택하세요.')
            selected=[name for name in defaults['algorithms'] if name in selected]
            if action=='stock_train':
                data_root,data=existing(parameters.get('data_job_id'),'stock_data')
                settings={'initial_amount':float(parameters.get('initial_amount',defaults['initial_amount'])),
                    'cost_pct':float(parameters.get('cost_pct',defaults['cost_pct'])),'total_timesteps':int(parameters.get('total_timesteps',defaults['total_timesteps']))}
                if settings['initial_amount']<=0 or settings['total_timesteps']<1 or settings['cost_pct']<0:raise ValueError('초기 자산·학습 단계·거래 비용 입력을 확인하세요.')
                training=frame(data_root/'train_data.csv');kwargs=environment(training,settings)
                record.update(data_job_id=data_root.name,settings=settings,env_kwargs=kwargs,
                    model_states={name:{'status':'queued','num_timesteps':0} for name in selected});save()
                (output/'trained_models').mkdir();(output/'results').mkdir()
                env=StockTradingEnv(df=training,**kwargs);env_train,_=env.get_sb_env()
                from stable_baselines3.common.logger import configure
                try:
                    agent=DRLAgent(env=env_train)
                    for name in selected:
                        row=record['model_states'][name];row['status']='running';save();print('FinRL 모델 학습 시작:',name,flush=True)
                        try:
                            model=agent.get_model(name,model_kwargs=dict(defaults['model_kwargs'][name]))
                            model.set_logger(configure(str(output/'results'/name),['stdout','csv','tensorboard']))
                            trained=agent.train_model(model=model,tb_log_name=name,total_timesteps=settings['total_timesteps'])
                            target=output/'trained_models'/('agent_'+name);trained.save(str(target))
                            filename='trained_models/agent_'+name+'.zip';record['files'].append(filename)
                            row.update(status='complete',num_timesteps=int(trained.num_timesteps),checkpoint=filename);save()
                        except Exception as exc:row.update(status='failed',error=str(exc));save();raise
                finally:env_train.close()
                record['value']={'models':record['model_states'],'stock_dimension':kwargs['stock_dim'],'state_space':kwargs['state_space']}
            else:
                training_root,trained=existing(parameters.get('training_job_id'),'stock_train')
                data_root,data=existing(trained['data_job_id'],'stock_data');settings=trained['settings']
                for name in selected:
                    if trained['model_states'].get(name,{}).get('status')!='complete':raise ValueError(name.upper()+'의 실제 학습 결과가 없습니다.')
                training=frame(data_root/'train_data.csv');trade=frame(data_root/'trade_data.csv')
                record.update(training_job_id=training_root.name,data_job_id=data_root.name,settings=settings,
                    model_states={name:{'status':'queued'} for name in selected});save()
                (output/'results').mkdir()
                env=StockTradingEnv(df=trade,turbulence_threshold=70,risk_indicator_col='vix',**environment(trade,settings));curves={}
                try:
                    for name in selected:
                        record['model_states'][name]['status']='running';save()
                        model=system.model(training_root/trained['model_states'][name]['checkpoint'],name)
                        account,_=DRLAgent.DRL_prediction(model=model,environment=env)
                        curves[name]=account.set_index(account.columns[0])['account_value']
                        record['model_states'][name]['status']='complete';save()
                finally:env.close()
                _,sources=stock_sources();source=sources['FinRL_StockTrading_2026_3_Backtest.py'];body=source['tree'].body
                start=next(i for i,node in enumerate(body) if isinstance(node,ast.FunctionDef) and node.name=='process_df_for_mvo')
                end=next(i for i,node in enumerate(body) if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='df_result_a2c' for t in node.targets))
                namespace={'np':np,'pd':pd,'train':training,'trade':trade,'TRADE_START_DATE':data['settings']['trade_start'],'TRADE_END_DATE':data['settings']['trade_end']}
                imports=[node for node in body[:start] if isinstance(node,(ast.Import,ast.ImportFrom))]
                exec(compile(ast.Module(body=imports,type_ignores=[]),str(source['path']),'exec'),namespace)
                exec(compile(ast.Module(body=body[start:end],type_ignores=[]),str(source['path']),'exec'),namespace)
                scale=settings['initial_amount']/defaults['initial_amount']
                curves['mvo']=namespace['MVO_result']['Mean Var']*scale;curves['dji']=namespace['dji']['close']*scale
                result=pd.DataFrame(curves);result.to_csv(output/'result.csv')
                import matplotlib.pyplot as plt
                plt.rcParams['figure.figsize']=(15,5);axes=result.plot();axes.set_title('Portfolio Value Over Time');axes.set_xlabel('Date');axes.set_ylabel('Portfolio Value ($)')
                plt.savefig(output/'backtest_result.png',dpi=150,bbox_inches='tight');plt.close('all')
                record.update(files=['result.csv','backtest_result.png'],figures=['backtest_result.png'],value=serialize(result))
        record['status']='complete';save();return record
