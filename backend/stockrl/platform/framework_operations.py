"""Common API dispatch, native calls, catalog and result handling."""
from __future__ import annotations
import ast
import dataclasses
import importlib.util
import json
import math
import sys
import tokenize
from functools import lru_cache
from pathlib import Path
from .. import ROOT
from ..finrl.framework import finrl_file
from ..finrl_trading import finrlx,SOURCE_ROOT
from ..finrl_trading.data import prices
from ..finrl_trading.operations import provider_environment
from ..state_io import atomic_json,read_json
from .module_inventory import source_definition

# Shared registry; execution belongs to each framework folder.
from ..finrl.operations import ACTIONS as FINRL_ACTIONS
from ..finrl_trading.operations import ACTIONS as TRADING_ACTIONS

ACTIONS={**FINRL_ACTIONS,**TRADING_ACTIONS,"native_call":('공식 모듈 직접 실행', 'native', None, '선택한 원본 함수 호출', ['module', 'callable', 'kwargs', 'init_kwargs', 'env_kwargs', 'steps', 'argv', 'symbols', 'source'])}



def action_list():
    return [{'id':key,'name':row[0],'menu':row[1],'module':row[2] or '요청에서 선택한 공식 모듈','function':row[3],
             'fields':row[4],'defaults':{'currency':'USD'},
             'api':'/api','operation':'framework/'+key,'stop_api':'/api','stop_operation':'stop'} for key,row in ACTIONS.items()]


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


def validate_native_call(parameters):
    target=parameters.get('module');name=parameters.get('callable','')
    item=next((item for item in source_catalog() if item['id']==target),None)
    if not item or item['framework'] not in ('FinRL-X','FinRL'):raise ValueError('공식 소스에 존재하는 모듈을 선택하세요.')
    if item['path'].startswith('FinRL-X/web/'):raise ValueError('Streamlit 화면 모듈은 실행하지 않습니다.')
    if name not in item['functions'] or any(part.startswith('_') for part in name.split('.')):raise ValueError('공식 공개 함수·클래스·메서드를 선택하세요.')
    if name.rsplit('.',1)[-1]=='remove_all_files':raise ValueError('영구 삭제 함수는 실행하지 않습니다.')
    def check(callable_name,value):
        if isinstance(value,str):value=json.loads(value or '{}')
        if not isinstance(value,dict):raise ValueError(callable_name+' 인자는 JSON 객체여야 합니다.')
        fields=item.get('parameters',{}).get(callable_name,[])
        missing=[field['name'] for field in fields if field['required'] and field['name'] not in value]
        if missing:raise ValueError(callable_name+' 필수 인자: '+', '.join(missing)+'; 공식 인자 양식을 사용하세요.')
        for field in fields:
            if field['name'] in value and field.get('annotation')=='str' and not isinstance(value[field['name']],str):
                raise ValueError(callable_name+'.'+field['name']+'는 공식 계약상 문자열입니다. 객체 변환 태그 대신 실제 문자열을 전달하세요.')
        contract=item.get('keyword_contracts',{}).get(callable_name)
        if contract:
            unexpected=set(value)-{field['name'] for field in fields}
            if unexpected and not contract['variadic']:raise ValueError(callable_name+'에 없는 인자: '+', '.join(sorted(unexpected)))
            positional=set(value)&set(contract['positional_only'])
            if positional:raise ValueError('위치 전용 인자는 JSON 키로 호출할 수 없습니다: '+', '.join(sorted(positional)))
        return value
    steps=parameters.get('steps',[])
    if isinstance(steps,str):steps=json.loads(steps or '[]')
    if not isinstance(steps,list):raise ValueError('메서드 연결은 JSON 배열이어야 합니다.')
    parts=name.split('.')
    if steps:
        check(parts[0]+'.__init__',parameters.get('init_kwargs',{}))
        for step in steps:
            if not isinstance(step,dict):raise ValueError('메서드 연결 항목은 JSON 객체여야 합니다.')
            method=step.get('method','');full=parts[0]+'.'+method
            if full not in item['functions'] or method.startswith('_'):raise ValueError('공식 공개 메서드를 선택하세요: '+full)
            check(full,step.get('kwargs',{}))
    else:
        fields=name if name in item.get('parameters',{}) else name+'.__init__'
        check(fields,parameters.get('kwargs',{}))
        if len(parts)==2 and item.get('keyword_contracts',{}).get(name,{}).get('instance'):
            check(parts[0]+'.__init__',parameters.get('init_kwargs',{}))
    return item


def native_call(parameters,output):
    """Invoke an explicitly selected public upstream callable without replacing its code."""
    import inspect
    import numpy as np
    import pandas as pd
    item=validate_native_call(parameters)
    target=parameters['module'];name=parameters['callable']
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
            context[value]=finrlx('strategies.adaptive_rotation.config_loader').load_config(str(parameters.get('config_path',SOURCE_ROOT/'src/strategies/AdaptiveRotationConf_v1.2.1.yaml')))
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












def _execute(action,parameters,output):
    if action not in ACTIONS:raise ValueError('등록된 공식 실행 기능이 아닙니다.')
    if action=='native_call':
        output=Path(output);output.mkdir(parents=True,exist_ok=True)
        return native_call({k:v for k,v in parameters.items() if v not in ('',None,[])},output)
    if action in FINRL_ACTIONS:
        from ..finrl.operations import execute
    else:
        from ..finrl_trading.operations import execute
    return execute(action,parameters,output)

def execute(action,parameters,output):
    """Record the actual official functions called by a successful task."""
    called={};previous=sys.getprofile();source_names={}
    finrl_root=Path(importlib.util.find_spec('finrl').origin).parent
    source_root=SOURCE_ROOT/'src'
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
    roots=[('stockrl',ROOT/'backend/stockrl'),('FinRL-X',SOURCE_ROOT/'src')]
    for framework,package in [('FinRL','finrl'),('SB3','stable_baselines3'),('SB3-Contrib','sb3_contrib')]:
        spec=importlib.util.find_spec(package)
        if spec and spec.origin:roots.append((framework,Path(spec.origin).parent))
    items=[]
    for framework,root in roots:
        for path in sorted(root.rglob('*.py')):
            if framework=='stockrl' and path.is_relative_to(SOURCE_ROOT):continue
            relative=path.relative_to(root).as_posix()
            module=relative.removesuffix('.py').replace('/','.').removesuffix('.__init__')
            item=source_definition(path,framework,module);item['path']=framework+'/'+relative
            items.append(item)
    script=SOURCE_ROOT/'deploy.sh'
    if script.is_file():items.append({'id':'FinRL-X:deploy','path':'FinRL-X/deploy.sh','framework':'FinRL-X',
        'source_path':str(script),'description':'공식 데이터 준비 및 전략 실행 절차','functions':[],
        'signatures':{},'imports':[],'calls':['data download','run_single_date','run_backtest']})
    return items


def catalog():
    from .system_operations import system
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
            elif imported=='stable_baselines3':target='SB3:__init__'
            elif imported.startswith('stable_baselines3.'):target='SB3:'+imported.removeprefix('stable_baselines3.')
            elif imported.startswith('sb3_contrib.'):target='SB3-Contrib:'+imported.removeprefix('sb3_contrib.')
            elif item['framework']=='FinRL-X' and imported.startswith(('strategies.','data.','config.','trading.','backtest.')):target='FinRL-X:'+imported
            else:continue
            if target in by_id:deps.append(target)
        edges[item['id']]=deps
    connected=set(roots);queue=list(roots)
    while queue:
        for target in edges.get(queue.pop(),[]):
            if target not in connected:connected.add(target);queue.append(target)
    verified={};failed={}
    for result_file in sorted((ROOT/'runtime/official/framework-jobs').glob('*/result.json'),key=lambda path:path.stat().st_mtime_ns):
        record=read_json(result_file)
        if record.get('error'):
            failed[record.get('module')]=record['error'];continue
        failed.pop(record.get('module'),None)
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
        item['native_api']='/api' if native else None
        item['native_operation']='framework/native_call' if native else None
        imported=system.states.get('import:'+item['id'])
        import_error=system.state_errors.get('import:'+item['id'])
        item['imported']=bool(imported and imported.get('imported'))
        item['import_error']=import_error
        item['verified_functions']=sorted(set(verified.get(item['id'],[])))
        external=any(word in item['id'].lower() for word in ('alpaca','wrds','eodhd','joinquant','sinopac','shioaji','tushare','ibkr','fxmacro','quantconnect'))
        if import_error:item.update(status='미연결',reason='백엔드 import 실패: '+import_error)
        elif item['verified_functions']:item.update(status='연결·정상 작동',reason='표시된 함수의 실제 실행 결과가 있습니다. 다른 함수까지 검증한 것은 아닙니다.')
        elif external:item.update(status='외부 인증 필요',reason='공식 공급원·계정 인증과 해당 입력 계약이 필요합니다. 다른 공급원으로 대체하지 않습니다.')
        elif item['backend_connected']:item.update(status='연결·실행 미확인',reason='원본 공개 callable 실행 API 또는 연결 모듈의 내부 의존성입니다. 필요한 원본 입력·객체·의존성을 갖춰 실행해야 합니다.')
        elif item['path'].startswith('FinRL-X/web/'):item.update(status='미연결',reason='사용자 지시로 Streamlit 화면은 이식·실행에서 제외합니다.')
        elif not public:item.update(status='미연결',reason='독립 실행 함수가 없는 패키지 초기화·상수 모듈 또는 소스 해석 오류입니다. 상위 공식 모듈의 import 경로로 사용됩니다.')
        else:item.update(status='미연결',reason='원본 입력·의존성 및 공개 실행 경로를 확인해야 합니다.')
        if item['imported']:item['reason']='백엔드 import 완료. '+item['reason']
    return {'items':items,'actions':action_list(),'counts':{status:sum(item['status']==status for item in items if item['framework']!='stockrl') for status in ('연결·정상 작동','연결·실행 미확인','미연결','외부 인증 필요')}}
