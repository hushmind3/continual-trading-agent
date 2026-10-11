"""Official framework catalog and task adapters, executed by the existing job worker."""
from __future__ import annotations
import ast
import dataclasses
import importlib.util
import json
import math
import sys
import subprocess
import tokenize
from functools import lru_cache
from pathlib import Path
from ..framework import ROOT,finrlx,finrl_file,prices
from ..state_io import atomic_json,read_json

# Values omitted by the UI are omitted from official calls, retaining their defaults.
ACTIONS={
 'native_call':('공식 모듈 직접 실행','native',None,'선택한 원본 함수 호출',['module','callable','kwargs','init_kwargs','symbols','source']),
 'finrl_workflow':('FinRL 원형 학습·평가·모의매매','workflows','FinRL:main','main',['mode']),
 'adaptive_download':('Adaptive Rotation 원형 데이터 준비','workflows','FinRL-X:deploy','deploy.sh::data download',['config_path','data_dir']),
 'adaptive_single':('Adaptive Rotation 원형 단일 실행','workflows','FinRL-X:strategies.run_adaptive_rotation_strategy','run_single_date',['config_path','data_dir','as_of_date']),
 'adaptive_backtest':('Adaptive Rotation 원형 전체 백테스트','workflows','FinRL-X:strategies.run_adaptive_rotation_strategy','run_backtest',['config_path','data_dir','start_date','end_date']),
 'calendar':('시장 거래일','markets','FinRL-X:data.trading_calendar','get_trading_days',['start_date','end_date','exchange']),
 'fundamentals':('FMP 재무 데이터 수집','markets','FinRL-X:data.data_fetcher','fetch_fundamental_data',['symbols','start_date','end_date']),
 'news':('FMP 뉴스 수집','markets','FinRL-X:data.data_fetcher','fetch_news',['symbol','start_date','end_date']),
 'nasdaq100':('NASDAQ 100 조회','markets','FinRL-X:data.data_fetcher','fetch_nasdaq100_tickers',[]),
 'sp500':('S&P 500 조회','markets','FinRL-X:data.data_fetcher','fetch_sp500_tickers',[]),
 'yahoo':('FinRL Yahoo 가격 수집','markets','FinRL:meta.preprocessor.yahoodownloader','YahooDownloader.fetch_data',['symbols','start_date','end_date']),
 'process_prices':('공식 가격 CSV 전처리','markets','FinRL-X:data.data_processor','process_prices',['source']),
 'process_fundamentals':('공식 재무 CSV 전처리','markets','FinRL-X:data.data_processor','process_fundamentals',['source']),
 'ml_dataset':('공식 ML 데이터 구성','markets','FinRL-X:data.data_processor','create_ml_dataset',['fundamentals','source','target_period']),
 'features':('FinRL 기술지표·전처리','markets','FinRL:meta.preprocessor.preprocessors','FeatureEngineer.preprocess_data',['currency','symbols']),
 'data_split':('FinRL 기간 분할','markets','FinRL:meta.preprocessor.preprocessors','data_split',['currency','symbols','start_date','end_date']),
 'tsmom':('공식 TSMOM 신호','markets','FinRL-X:strategies.tsmomsignal','TSMOMSignalEngine.generate_signal_one_ticker',['currency','symbols']),
 'adaptive':('공식 Adaptive Rotation','portfolio','FinRL-X:strategies.adaptive_rotation.adaptive_rotation_engine','AdaptiveRotationEngine.run',['currency','symbols','config_path','as_of_date']),
 'equal_weight':('공식 동일 비중 전략','portfolio','FinRL-X:strategies.base_strategy','EqualWeightStrategy.generate_weights',['fundamentals']),
 'ml':('공식 ML 종목 선택','portfolio','FinRL-X:strategies.ml_strategy','MLStockSelectionStrategy.generate_weights',['fundamentals','source','prediction_mode','weight_method']),
 'sector_ml':('공식 산업별 ML 종목 선택','portfolio','FinRL-X:strategies.ml_strategy','SectorNeutralMLStrategy.generate_weights',['fundamentals','source','prediction_mode','weight_method']),
 'performance':('공식 수익·성과 지표','portfolio','FinRL-X:trading.performance_analyzer','compute_performance_metrics',['currency','symbol']),
 'finrl_stats':('FinRL 백테스트 성과','portfolio','FinRL:plot','backtest_stats',['currency']),
 'config_check':('FinRL-X 설정 유효성','connection','FinRL-X:config.settings','validate_config',[]),
}


def action_list():
    return [{'id':key,'name':row[0],'menu':row[1],'module':row[2] or '요청에서 선택한 공식 모듈','function':row[3],
             'fields':row[4],'defaults':{'currency':'USD'},
             'api':'/api/framework/'+key,'stop_api':'/api/stop'} for key,row in ACTIONS.items()]


def serialize(value):
    import numpy as np
    import pandas as pd
    if dataclasses.is_dataclass(value):return serialize(dataclasses.asdict(value))
    if hasattr(value,'model_dump'):return serialize(value.model_dump())
    if isinstance(value,pd.DataFrame):
        frame=value.reset_index()
        return {'columns':[str(c) for c in frame.columns],'total_rows':len(frame),'rows':serialize(frame.to_dict('records'))}
    if isinstance(value,pd.Series):return serialize(value.to_dict())
    if isinstance(value,dict):return {str(k):('[보안 값 숨김]' if any(token in str(k).lower() for token in ('password','secret','api_key','token')) and v else serialize(v)) for k,v in value.items()}
    if isinstance(value,(list,tuple,np.ndarray)):return [serialize(v) for v in value]
    if isinstance(value,np.generic):return serialize(value.item())
    if isinstance(value,float):return value if math.isfinite(value) else None
    if value is None or isinstance(value,(str,int,bool)):return value
    return str(value)


def native_call(parameters,output):
    """Invoke an explicitly selected public upstream callable without replacing its code."""
    import inspect
    import numpy as np
    import pandas as pd
    target=parameters.get('module');name=parameters.get('callable','')
    item=next((item for item in source_catalog() if item['id']==target),None)
    if not item or item['framework'] not in ('FinRL-X','FinRL'):raise ValueError('공식 소스에 존재하는 모듈을 선택하세요.')
    if item['path'].startswith('FinRL-X/web/'):raise ValueError('Streamlit 화면 모듈은 이식·실행하지 않습니다.')
    if name not in item['functions'] or any(part.startswith('_') for part in name.split('.')):raise ValueError('원본에 선언된 공개 함수·클래스·메서드를 선택하세요.')
    if name.rsplit('.',1)[-1] in ('remove_all_files',):raise ValueError('영구 삭제 함수는 휴지통 정책에 따라 실행하지 않습니다.')
    module_name=target.split(':',1)[1]
    module=finrlx(module_name) if item['framework']=='FinRL-X' else finrl_file(module_name.replace('.','/')+'.py')
    def arguments(key):
        value=parameters.get(key,{})
        if isinstance(value,str):value=json.loads(value or '{}')
        if not isinstance(value,dict):raise ValueError(key+'는 원본 인자 이름을 키로 사용하는 JSON 객체입니다.')
        return value
    context={}
    def resolve(value):
        if isinstance(value,dict) and set(value)=={'$timestamp'}:return pd.Timestamp(value['$timestamp'])
        if isinstance(value,dict) and set(value)=={'$timedelta'}:return pd.Timedelta(**value['$timedelta'])
        if isinstance(value,dict) and set(value)=={'$tensor'}:
            import torch
            return torch.as_tensor(resolve(value['$tensor']))
        if isinstance(value,dict):return {key:resolve(item) for key,item in value.items()}
        if isinstance(value,list):return [resolve(item) for item in value]
        if not isinstance(value,str) or not value.startswith('$'):return value
        if value.startswith('$credential:'):
            import os
            key=value.partition(':')[2];saved=provider_environment()
            secret=saved.get(key) or os.environ.get(key)
            if not secret:raise ValueError('공급원 보안 설정에 '+key+' 값이 없습니다.')
            return secret
        if value in context:return context[value]
        if value=='$data':
            if parameters.get('source'):_,data=csv_input(parameters,'source')
            else:
                symbols=parameters.get('symbols')
                if isinstance(symbols,str):symbols=[s.strip() for s in symbols.split(',') if s.strip()]
                data=prices(None,symbols).rename(columns={'symbol':'tic'})
            if data.empty:raise ValueError('실제 입력 데이터가 없습니다.')
            context[value]=data
        elif value=='$series':
            data=resolve('$data');column=parameters.get('column','close')
            if data.get('tic',pd.Series(dtype=str)).nunique()>1:raise ValueError('$series에는 종목 1개를 선택하세요.')
            context[value]=data.set_index('date')[column]
        elif value=='$array':context[value]=resolve('$data').select_dtypes(include='number').to_numpy()
        elif value=='$price_data':
            data=resolve('$data');context[value]={symbol:frame.set_index('date').close for symbol,frame in data.groupby('tic')}
        elif value=='$initial_amount':
            from finrl import config
            context[value]=config.INITIAL_AMOUNT
        elif value=='$config':context[value]=finrlx('config.settings').get_config()
        elif value=='$rotation_config':
            context[value]=finrlx('strategies.adaptive_rotation.config_loader').load_config(str(parameters.get('config_path',ROOT/'FinRL-X/src/strategies/AdaptiveRotationConf_v1.2.1.yaml')))
        elif value=='$indicators':
            from finrl import config
            context[value]=config.INDICATORS
        elif value=='$env':
            data=resolve('$data')
            context[value]=finrl_file('meta/env_portfolio_optimization/env_portfolio_optimization.py').PortfolioOptimizationEnv(
                df=data,**resolve(arguments('env_kwargs')))
        else:raise ValueError('정의되지 않은 입력 참조: '+value)
        return context[value]
    parts=name.split('.');constructor=getattr(module,parts[0]);kwargs=resolve(arguments('kwargs'))
    previous_argv=sys.argv
    argv=parameters.get('argv',[])
    if isinstance(argv,str):argv=json.loads(argv or '[]')
    if not isinstance(argv,list) or not all(isinstance(arg,str) for arg in argv):raise ValueError('원본 CLI 인자는 문자열 JSON 배열입니다.')
    if item['framework']=='FinRL-X' and module_name=='main' and 'dashboard' in argv:raise ValueError('Streamlit 실행은 제외합니다.')
    instance=None
    try:
        sys.argv=[item['path'],*argv]
        steps=parameters.get('steps',[])
        if isinstance(steps,str):steps=json.loads(steps or '[]')
        if steps:
            instance=constructor(**resolve(arguments('init_kwargs')));context['$instance']=instance
            for step in steps:
                method=step['method']
                if parts[0]+'.'+method not in item['functions'] or method.startswith('_'):raise ValueError('원본 클래스의 공개 메서드가 아닙니다: '+method)
                function=getattr(instance,method);value=function(**resolve(step.get('kwargs',{})))
                if step.get('save_as'):context['$'+step['save_as']]=value
        elif len(parts)==1:
            inspect.signature(constructor).bind(**kwargs);value=constructor(**kwargs)
        elif len(parts)==2:
            descriptor=inspect.getattr_static(constructor,parts[1])
            if isinstance(descriptor,(staticmethod,classmethod)):function=getattr(constructor,parts[1])
            else:
                init=resolve(arguments('init_kwargs'));inspect.signature(constructor).bind(**init)
                instance=constructor(**init);function=getattr(instance,parts[1])
            if callable(function):inspect.signature(function).bind(**kwargs);value=function(**kwargs)
            elif not kwargs:value=function
            else:raise ValueError('원본 속성에는 함수 인자를 전달하지 않습니다.')
        else:raise ValueError('원본 공개 callable 경로가 유효하지 않습니다.')
    finally:sys.argv=previous_argv
    # Constructor results are metadata, never a claim that a new model is trained.
    import torch
    model_state=None
    if instance is not None and isinstance(instance,torch.nn.Module):model_state='새 원본 클래스 인스턴스 · 기존 가중치 로딩·학습 미확인'
    if isinstance(value,torch.nn.Module):
        value={'class':type(value).__name__,'parameters':sum(p.numel() for p in value.parameters()),
               'structure':str(value),'trained':'생성만 확인 · 학습·추론 미확인'}
    elif hasattr(value,'action_space') and hasattr(value,'observation_space'):
        value={'class':type(value).__name__,'action_space':str(value.action_space),'observation_space':str(value.observation_space),
               'state':'구성만 확인 · step 실행 미확인'}
    if isinstance(value,pd.DataFrame):value.to_csv(output/'result.csv',index=False)
    if isinstance(value,torch.Tensor):value=value.detach().cpu().numpy()
    return {'action':'native_call','module':target,'function':name,'value':serialize(value),'model_state':model_state,'output':str(output.relative_to(ROOT))}


def csv_input(parameters,key):
    import pandas as pd
    path=Path(parameters.get(key,'')).expanduser().resolve()
    if not path.is_file() or path.suffix.lower()!='.csv':raise ValueError(key+': 실제 CSV 파일 경로가 필요합니다.')
    if (ROOT/'휴지통').resolve() in path.parents:raise ValueError('휴지통은 입력으로 사용하지 않습니다.')
    return path,pd.read_csv(path)


def preview(value):
    if isinstance(value,dict):return {key:preview(item) for key,item in value.items()}
    if isinstance(value,list):return [preview(item) for item in value[:100]]
    return value


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


def _execute(action,parameters,output):
    import pandas as pd
    if action not in ACTIONS:raise ValueError('등록된 공식 실행 기능이 아닙니다.')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    p={key:value for key,value in parameters.items() if value not in ('',None,[])}
    row=ACTIONS[action]
    if action=='native_call':return native_call(p,output)
    if action=='finrl_workflow':
        mode=p.get('mode','train')
        if mode not in ('train','test','trade'):raise ValueError('공식 FinRL mode는 train / test / trade입니다.')
        print('FinRL 원형 main 실행 · 기본 Elegantrl PPO · 기존 SAC 운영 모델을 교체하지 않습니다.',flush=True)
        subprocess.run([sys.executable,'-m','finrl.main','--mode',mode],cwd=output,check=True,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        return {'action':action,'module':row[2],'function':row[3],'value':{'mode':mode,'output':str(output),'policy':'공식 main 기본 PPO'},'output':str(output.relative_to(ROOT))}
    if action=='adaptive_download':
        import re
        script=ROOT/'FinRL-X/deploy.sh';source=script.read_text(encoding='utf-8')
        match=re.search(r'python3 - "\$CONFIG" "\$DATA_DIR" <<\x27PYEOF\x27\n(.*?)\nPYEOF',source,re.S)
        if not match:raise ValueError('공식 deploy.sh의 데이터 준비 실행 블록을 찾지 못했습니다.')
        config=str(Path(p.get('config_path',ROOT/'FinRL-X/src/strategies/AdaptiveRotationConf_v1.2.1.yaml')).resolve())
        directory=Path(p.get('data_dir',ROOT/'FinRL-X/data/fmp_daily')).resolve();directory.mkdir(parents=True,exist_ok=True)
        print('공식 deploy.sh 데이터 준비 블록 실행:',directory,flush=True)
        subprocess.run([sys.executable,'-',config,str(directory)],input=match.group(1),text=True,encoding='utf-8',
            cwd=ROOT/'FinRL-X',check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        return {'action':action,'module':row[2],'function':row[3],'value':{'data_dir':str(directory),'config':config},'output':str(output.relative_to(ROOT))}
    module=finrlx(row[2].split(':',1)[1]) if row[2].startswith('FinRL-X:') else finrl_file(row[2].split(':',1)[1].replace('.','/')+'.py')
    currency=p.get('currency','USD');symbols=p.get('symbols') or ([p['symbol']] if p.get('symbol') else None)
    if isinstance(symbols,str):symbols=[s.strip() for s in symbols.split(',') if s.strip()]
    print('공식 함수 실행:',row[2],row[3],flush=True)
    if action in ('adaptive_single','adaptive_backtest'):
        config=str(Path(p.get('config_path',ROOT/'FinRL-X/src/strategies/AdaptiveRotationConf_v1.2.1.yaml')).resolve())
        kwargs={'data_dir':p['data_dir']} if p.get('data_dir') else {}
        from contextlib import chdir
        with chdir(ROOT/'FinRL-X'):
            if action=='adaptive_single':value=module.run_single_date(config,p['as_of_date'],**kwargs)
            else:value=module.run_backtest(config,p['start_date'],p['end_date'],**kwargs)
    elif action=='calendar':
        kwargs={'exchange':p['exchange']} if p.get('exchange') else {}
        value=module.get_trading_days(p['start_date'],p['end_date'],**kwargs)
    elif action=='sp500':value=module.fetch_sp500_tickers(output_path=str(output/'sp500.csv'))
    elif action=='nasdaq100':value=module.fetch_nasdaq100_tickers()
    elif action=='fundamentals':value=module.fetch_fundamental_data(symbols,p['start_date'],p['end_date'])
    elif action=='news':value=module.fetch_news(p['symbol'],p['start_date'],p['end_date'])
    elif action=='yahoo':value=module.YahooDownloader(start_date=p['start_date'],end_date=p['end_date'],ticker_list=symbols).fetch_data()
    elif action in ('process_prices','process_fundamentals'):
        source,_=csv_input(p,'source')
        function=module.process_prices if action=='process_prices' else module.process_fundamentals
        value=function(str(source),str(output/'processed.csv'))
    elif action=='ml_dataset':
        fundamentals,_=csv_input(p,'fundamentals');source,_=csv_input(p,'source')
        value=module.DataProcessor(data_dir=str(output)).create_ml_dataset(str(fundamentals),str(source),**({'target_period':int(p['target_period'])} if 'target_period' in p else {}))
    elif action in ('equal_weight','ml','sector_ml'):
        _,fundamentals=csv_input(p,'fundamentals');data={'fundamentals':fundamentals}
        if p.get('source'):_,data['prices']=csv_input(p,'source')
        cls={'equal_weight':'EqualWeightStrategy','ml':'MLStockSelectionStrategy','sector_ml':'SectorNeutralMLStrategy'}[action]
        config=finrlx('strategies.base_strategy').StrategyConfig()
        result=getattr(module,cls)(config).generate_weights(data,**{k:p[k] for k in ('prediction_mode','weight_method') if k in p})
        if result.metadata and result.metadata.get('error'):raise ValueError(str(result.metadata['error']))
        value={'weights':result.weights,'metadata':result.metadata}
    elif action=='finrl_stats':
        file=ROOT/'runtime/official/backtests'/currency/'backtest.csv'
        if not file.is_file():raise ValueError(currency+' 실제 백테스트 결과가 없습니다.')
        data=pd.read_csv(file);data.columns=['date','account_value'] if len(data.columns)==2 else data.columns
        value=module.backtest_stats(data)
    elif action=='config_check':
        value=module.validate_config()
    else:
        frame=prices(None if action=='adaptive' else currency,symbols)
        if frame.empty:raise ValueError('선택 종목의 실제 저장 가격이 없습니다.')
        if action=='features':value=module.FeatureEngineer().preprocess_data(frame.rename(columns={'symbol':'tic'}))
        elif action=='data_split':value=module.data_split(frame.rename(columns={'symbol':'tic'}),p['start_date'],p['end_date'])
        elif action=='performance':value=module.compute_performance_metrics(frame.sort_values('date').set_index('date').close)
        elif action=='tsmom':
            engine=module.TSMOMSignalEngine()
            value={symbol:engine.generate_signal_one_ticker(data.rename(columns={'symbol':'tic'})) for symbol,data in frame.groupby('symbol')}
        elif action=='adaptive':
            config=Path(p.get('config_path',ROOT/'FinRL-X/src/strategies/AdaptiveRotationConf_v1.2.1.yaml')).expanduser().resolve()
            if not config.is_file():raise ValueError('실제 Adaptive Rotation YAML 경로가 필요합니다.')
            preprocessing=finrlx('strategies.adaptive_rotation.data_preprocessor')
            calendar=finrlx('strategies.adaptive_rotation.utils.calendar_utils')
            week_ends=calendar.get_week_end_dates(str(frame.date.min().date()),str(frame.date.max().date()))
            weekly=preprocessing.aggregate_multiple_symbols_to_weekly({symbol:data.set_index('date') for symbol,data in frame.groupby('symbol')},week_ends)
            series={symbol:data.close for symbol,data in weekly.items()}
            weights,audit=module.AdaptiveRotationEngine(config_path=str(config)).run(series,p.get('as_of_date',str(frame.date.max().date())))
            value={'weights':weights,'audit':audit}
        else:raise ValueError('실행 어댑터가 없습니다.')
    if isinstance(value,pd.DataFrame):value.to_csv(output/'result.csv',index=False)
    result={'action':action,'module':row[2],'function':row[3],'output':str(output.relative_to(ROOT)), 'value':serialize(value)}
    atomic_json(result,output/'result.json')
    print('공식 함수 실행 완료:',row[3],flush=True)
    return result


def execute(action,parameters,output):
    """Record the actual official functions called by a successful task."""
    called={};previous=sys.getprofile();source_names={}
    finrl_root=Path(importlib.util.find_spec('finrl').origin).parent
    source_root=ROOT/'FinRL-X/src'
    def trace(frame,event,arg):
        if event!='call':return
        filename=frame.f_code.co_filename
        if filename not in source_names:
            path=Path(filename)
            if path.is_relative_to(source_root):framework='FinRL-X';root=source_root
            elif path.is_relative_to(finrl_root):framework='FinRL';root=finrl_root
            else:source_names[filename]=None;return
            source_names[filename]=framework+':'+path.relative_to(root).as_posix().removesuffix('.py').replace('/','.')
        module=source_names[filename]
        if module is None:return
        called.setdefault(module,set()).add(frame.f_code.co_qualname)
    try:
        sys.setprofile(trace)
        result=_execute(action,parameters,output)
    finally:sys.setprofile(previous)
    result['executed_functions']={module:sorted(names) for module,names in called.items()}
    import matplotlib.pyplot as plt
    figures=[]
    for number in plt.get_fignums():
        name='figure_'+str(number)+'.png';plt.figure(number).savefig(Path(output)/name)
        figures.append(name)
    if figures:result['figures']=figures
    plt.close('all')
    atomic_json(result,Path(output)/'result.json')
    return result


@lru_cache(maxsize=1)
def source_catalog():
    """Inventory every real Python source, without executing package import side effects."""
    finrl_root=Path(importlib.util.find_spec('finrl').origin).parent
    roots=[('stockrl',ROOT/'src/stockrl'),('FinRL-X',ROOT/'FinRL-X/src'),('FinRL',finrl_root)]
    items=[]
    for framework,root in roots:
        for path in sorted(root.rglob('*.py')):
            relative=path.relative_to(root).as_posix();module=relative.removesuffix('.py').replace('/','.').removesuffix('.__init__')
            name=framework+':'+module
            try:
                with tokenize.open(path) as source:tree=ast.parse(source.read())
            except (UnicodeError,SyntaxError) as exc:
                items.append({'path':framework+'/'+relative,'id':name,'framework':framework,'description':str(exc),'functions':[],'imports':[],'calls':[]});continue
            functions=[];signatures={};parameters={};imports=[];calls=[]
            def arguments(node):
                positional=[*node.args.posonlyargs,*node.args.args]
                defaults=[None]*(len(positional)-len(node.args.defaults))+node.args.defaults
                fields=[]
                for arg,default in [*zip(positional,defaults),*zip(node.args.kwonlyargs,node.args.kw_defaults)]:
                    if arg.arg in ('self','cls'):continue
                    fields.append({'name':arg.arg,'annotation':ast.unparse(arg.annotation) if arg.annotation else None,
                        'required':default is None,'default':ast.unparse(default) if default is not None else None})
                return fields
            for node in ast.walk(tree):
                if isinstance(node,ast.ImportFrom):
                    imports.append('.'*node.level+(node.module or ''))
                elif isinstance(node,ast.Import):imports.extend(alias.name for alias in node.names)
                elif isinstance(node,ast.Call):
                    calls.append(ast.unparse(node.func))
                    if isinstance(node.func,ast.Name) and node.func.id in ('finrlx','finrl_file') and node.args and isinstance(node.args[0],ast.Constant):
                        imports.append(('src.' if node.func.id=='finrlx' else 'finrl.')+str(node.args[0].value).removesuffix('.py').replace('/','.'))
            for node in tree.body:
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    functions.append(node.name);signatures[node.name]=ast.unparse(node.args);parameters[node.name]=arguments(node)
                elif isinstance(node,ast.ClassDef):
                    functions.append(node.name)
                    for child in node.body:
                        if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef)):
                            key=node.name+'.'+child.name;functions.append(key);signatures[key]=ast.unparse(child.args);parameters[key]=arguments(child)
            items.append({'path':framework+'/'+relative,'id':name,'framework':framework,'description':ast.get_docstring(tree),
                          'functions':functions,'signatures':signatures,'parameters':parameters,'imports':sorted(set(imports)),'calls':sorted(set(calls))})
    script=ROOT/'FinRL-X/deploy.sh'
    if script.is_file():items.append({'id':'FinRL-X:deploy','path':'FinRL-X/deploy.sh','framework':'FinRL-X',
        'description':'공식 배포 스크립트의 데이터 준비 및 전략 실행 절차','functions':[],
        'signatures':{},'imports':[],'calls':['data download','run_single_date','run_backtest']})
    return items


def catalog():
    items=[dict(item) for item in source_catalog()];by_id={item['id']:item for item in items}
    roots={row[2]:[key] for key,row in ACTIONS.items() if row[2]}
    for item in items:
        if item['framework']=='stockrl':roots.setdefault(item['id'],[])
    edges={}
    for item in items:
        deps=[]
        for imported in item['imports']:
            if imported.startswith('.'):
                level=len(imported)-len(imported.lstrip('.'));parts=item['id'].split(':')[1].split('.')[:-level]
                target=item['framework']+':'+'.'.join(parts+[imported.lstrip('.')])
            elif imported.startswith('src.'):target='FinRL-X:'+imported[4:]
            elif imported.startswith('finrl.'):target='FinRL:'+imported[6:]
            elif imported.startswith('stockrl.'):target='stockrl:'+imported[8:]
            elif item['framework']=='FinRL-X' and imported.startswith(('strategies.','data.','config.','trading.','backtest.')):target='FinRL-X:'+imported
            else:continue
            if target in by_id:deps.append(target)
        edges[item['id']]=deps
    connected=set(roots);queue=list(roots)
    while queue:
        for target in edges.get(queue.pop(),[]):
            if target not in connected:connected.add(target);queue.append(target)
    verified={};failed={}
    for result_file in (ROOT/'runtime/official/framework-jobs').glob('*/result.json'):
        record=read_json(result_file)
        if record.get('error'):
            failed[record.get('module')]=record['error'];continue
        for module,names in record.get('executed_functions',{}).items():verified.setdefault(module,[]).extend(names)
        if record.get('module'):verified.setdefault(record['module'],[]).append(record.get('function'))
    for item in items:
        item.setdefault('signatures',{})
        item['last_error']=failed.get(item['id'])
        item['dependencies']=edges[item['id']];item['actions']=[key for key,row in ACTIONS.items() if row[2]==item['id']]
        public=bool([name for name in item['functions'] if all(not part.startswith('_') for part in name.split('.'))])
        native=public and item['framework'] in ('FinRL-X','FinRL') and not item['path'].startswith('FinRL-X/web/')
        item['backend_connected']=item['id'] in connected or native
        item['frontend']=bool(item['actions']) or native or item['id'] in connected
        item['native_api']='/api/framework/native_call' if native else None
        item['verified_functions']=sorted(set(verified.get(item['id'],[])))
        external=any(word in item['id'].lower() for word in ('alpaca','wrds','eodhd','joinquant','sinopac','shioaji','tushare','ibkr','fxmacro','quantconnect'))
        if item['verified_functions']:item.update(status='연결·정상 작동',reason='표시된 함수의 실제 실행 결과가 있습니다. 다른 함수까지 검증한 것은 아닙니다.')
        elif external:item.update(status='외부 인증 필요',reason='공식 공급원·계정 인증과 해당 입력 계약이 필요합니다. 다른 공급원으로 대체하지 않습니다.')
        elif item['backend_connected']:item.update(status='연결·실행 미확인',reason='원본 공개 callable 실행 API 또는 연결 모듈의 내부 의존성입니다. 필요한 원본 입력·객체·의존성을 갖춰 실행해야 합니다.')
        elif item['path'].startswith('FinRL-X/web/'):item.update(status='미연결',reason='사용자 지시로 Streamlit 화면은 이식·실행에서 제외합니다.')
        elif not public:item.update(status='미연결',reason='독립 실행 함수가 없는 패키지 초기화·상수 모듈 또는 소스 해석 오류입니다. 상위 공식 모듈의 import 경로로 사용됩니다.')
        else:item.update(status='미연결',reason='원본 입력·의존성 및 공개 실행 경로를 확인해야 합니다.')
    return {'items':items,'actions':action_list(),'counts':{status:sum(item['status']==status for item in items if item['framework']!='stockrl') for status in ('연결·정상 작동','연결·실행 미확인','미연결','외부 인증 필요')}}
