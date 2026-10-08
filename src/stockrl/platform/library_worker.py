"""Expert admission and composition jobs, isolated from the API and normal learner."""
import argparse
import time
from pathlib import Path
import torch
from ..state_io import atomic_json,read_json
from ..market_reader import IncrementalMarketCSV
from .config import load_settings
from .expert_packages import split_asset,load_package,package_path,HEADER_FORMAT
from .expert_contracts import input_contract
from .library_store import save_catalog,catalog_path,fetch_source,inspect_source,import_package
from .library_composition import publish_header
from .assets import ExpertPool,guard_model_assets
from .expert_inputs import snapshot_for
from .observations import prepare_evidence
from .journal import Journal
from .package_disposal import recycle


def probe(settings,item):
    settings=settings.model_copy(deep=True)
    key=item['id'];reference=item['package']
    if not item['input']['supported']:raise ValueError(item['input']['reason'])
    # Admission runs alongside market inference. Reserve GPU use for the live service.
    original_devices=dict(settings.resources.expert_devices);settings.resources.expert_devices[key]='cpu'
    weight_reads=guard_model_assets(settings.resolve(settings.expert_checkpoint),[reference])
    pool=ExpertPool(settings,extra_packages={key:reference})
    journal=Journal(settings.state_dir/'operations.sqlite3')
    try:
        reader=IncrementalMarketCSV(settings.state_dir/'live'/'market.csv',retain_timestamps=256)
        frame,_=reader.refresh()
        if frame is None or frame.empty:raise ValueError('실제 시세를 수집한 뒤 검사하세요.')
        batches,snapshot=snapshot_for(pool.entries[key],frame,journal,reader.path.with_name('timeframes.sqlite3'))
        started=time.perf_counter();packets=[]
        for data in batches[:1]:packets.append(pool.run(key,data,snapshot))
        spec=dict(expert_ids=[key],config=dict(feature_sizes={key:item['feature_size']},
                  stock_policy_ids=[key] if item['role']=='action' else []))
        tokens,mask,_=prepare_evidence({key:packets},packets[0]['symbols'],spec,snapshot['as_of'])
        if not mask.any():raise ValueError('현재 시점에 사용할 수 있는 원본 출력이 없습니다. 입력 날짜와 갱신 상태를 확인하세요.')
        return dict(status='passed',detail='실제 입력·출력 크기·고정 가중치 검사 통과',tested=time.time(),
            package_sha256=reference['sha256'],input_as_of=snapshot['as_of'],output_as_of=packets[0]['as_of'],
            output_shape=packets[0].get('output_shape'),seconds=time.perf_counter()-started,
            weight_files=sorted(weight_reads),metrics=pool.metrics[key])
    finally:pool.close();journal.close();settings.resources.expert_devices=original_devices


def apply(settings,header,catalog,active,progress):
    for key in active:
        if key not in catalog['experts']:raise ValueError('라이브러리에 없는 Expert: '+key)
        item=catalog['experts'][key];check=item['check']
        if check.get('status')!='passed' or check.get('package_sha256')!=item['package']['sha256']:
            raise ValueError('현재 패키지의 실제 추론 검사를 먼저 통과해야 합니다: '+item['name'])
        package=load_package(settings.resolve(settings.expert_checkpoint),item['package'],verify=True)
        header['expert_mapping'][key]=package['entry'];header['expert_packages'][key]=item['package']
        header['config']['feature_sizes'][key]=package['feature_size']
        header['config']['native_module_counts'][key]=package['module_count']
        policies=header['config'].setdefault('stock_policy_ids',[])
        if item['role']=='action' and key not in policies:policies.append(key)
    result=publish_header(settings,header,active,progress)
    catalog['active']=sorted(active);atomic_json(catalog,catalog_path(settings))
    return result


def run(config,request_path):
    settings=load_settings(config);torch.set_num_threads(settings.learning.cpu_threads)
    job=settings.state_dir/'library-job.json';request=read_json(request_path);kind=request['kind'];payload=request['payload']
    def progress(**values):atomic_json({**read_json(job),**values,'heartbeat':time.time()},job)
    progress(stage='loading',detail='구성과 고정 가중치 패키지를 확인하는 중')
    model=settings.resolve(settings.expert_checkpoint)
    header=split_asset(model,progress)
    catalog=save_catalog(settings,header)
    if header['config'].get('router_family')!='per-expert-context-v1':
        publish_header(settings,header,header.get('active_experts',settings.enabled_experts or sorted(header['expert_mapping'])),progress)
        header=torch.load(model,map_location='cpu',weights_only=True)
        catalog=save_catalog(settings,header,catalog)
    result=None
    if kind=='prepare':
        # Existing operational evidence proves current contracts; new packages always need a dry run.
        journal=Journal(settings.state_dir/'operations.sqlite3')
        try:
            metrics=journal.get_state('expert_metrics') or {}
            for key,item in catalog['experts'].items():
                metric=metrics.get(key,{})
                if metric.get('status')=='ready' and item['input']['supported']:
                    item['check']=dict(status='passed',detail='현재 운영에서 원본 추론 확인',tested=time.time(),
                        package_sha256=item['package']['sha256'],metrics=metric)
        finally:journal.close()
    elif kind=='inspect':
        path=fetch_source(settings,payload.get('source',''),progress)
        result=dict(source=str(path),experts=inspect_source(path,settings,catalog))
    elif kind=='import':
        path=fetch_source(settings,payload.get('source',''),progress)
        key=payload.get('expert_id','');slot=payload.get('slot',key)
        if slot in catalog['experts']:raise ValueError('동일 슬롯이 있습니다. 새 버전은 별도의 슬롯 이름을 지정하세요.')
        item=import_package(settings,path,key,slot,progress,catalog['experts'].get(key))
        catalog['experts'][slot]=item
        progress(stage='probing',expert=slot,detail='실제 시장·계좌 입력으로 추가 전 검사')
        try:item['check']=probe(settings,item)
        except Exception as exc:item['check']=dict(status='failed',detail=str(exc),tested=time.time())
        result=item
    elif kind=='probe':
        key=payload.get('id','')
        if key not in catalog['experts']:raise ValueError('등록되지 않은 패키지')
        progress(stage='probing',expert=key,detail='실제 입력으로 추론 검사 중')
        try:catalog['experts'][key]['check']=probe(settings,catalog['experts'][key])
        except Exception as exc:catalog['experts'][key]['check']=dict(status='failed',detail=str(exc),tested=time.time())
        result=catalog['experts'][key]['check']
    elif kind=='compare':
        from .expert_comparison import compare
        result=compare(settings,config,catalog,payload,progress)
        catalog['comparison']=result
    elif kind=='apply':
        result=apply(settings,header,catalog,list(payload.get('active',[])),progress)
        catalog['installed']={k:r['sha256'] for k,r in header['expert_packages'].items()}
    elif kind=='delete':
        key=payload.get('id','')
        if key not in catalog['experts']:raise ValueError('등록되지 않은 패키지')
        item=catalog['experts'][key];active=[k for k in catalog.get('active',[]) if k!=key]
        header['expert_mapping'].pop(key,None);header['expert_packages'].pop(key,None)
        for field in ('feature_sizes','native_module_counts'):header['config'][field].pop(key,None)
        header['config']['stock_policy_ids']=[k for k in header['config'].get('stock_policy_ids',[]) if k!=key]
        if not any(not e.get('stock_policy') for e in header['expert_mapping'].values()):raise ValueError('시장 분석 슬롯 하나는 남겨 두세요.')
        result=publish_header(settings,header,active,progress)
        file=package_path(model,item['package']);recycle(file)
        catalog['experts'].pop(key);catalog['active']=active
        catalog['installed']={k:r['sha256'] for k,r in header['expert_packages'].items()}
    atomic_json(catalog,catalog_path(settings));atomic_json(settings.model_dump(),Path(config))
    progress(stage='complete',result=result,detail='완료 · 기존 학습 상태 유지',finished=time.time())


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--request',type=Path,required=True)
    args=parser.parse_args()
    try:run(args.config,args.request)
    except Exception as exc:
        settings=load_settings(args.config);path=settings.state_dir/'library-job.json'
        atomic_json({**read_json(path),'stage':'error','error':f'{type(exc).__name__}: {exc}','finished':time.time()},path)
        raise
