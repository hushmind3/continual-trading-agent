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
from .expert_inputs import snapshot_for,admission_input
from .observations import prepare_evidence
from .journal import Journal
from .package_disposal import recycle
from .work_devices import choose_device


def probe(settings,item,device='auto'):
    settings=settings.model_copy(deep=True)
    key=item['id'];reference=item['package']
    if not item['input']['supported']:raise ValueError(item['input']['reason'])
    choice=choose_device(settings,device,item['package']['bytes'],item.get('check',{}).get('metrics',{}).get('peak_vram_bytes',0))
    original_devices=dict(settings.resources.expert_devices);settings.resources.expert_devices[key]=choice['device']
    weight_reads=guard_model_assets(settings.resolve(settings.expert_checkpoint),[reference])
    pool=ExpertPool(settings,extra_packages={key:reference})
    journal=Journal(settings.state_dir/'operations.sqlite3')
    try:
        reader=IncrementalMarketCSV(settings.state_dir/'live'/'market.csv',retain_timestamps=256)
        frame,_=reader.refresh()
        if frame is None or frame.empty:raise ValueError('실제 시세를 수집한 뒤 검사하세요.')
        batches,snapshot=snapshot_for(pool.entries[key],frame,journal,reader.path.with_name('timeframes.sqlite3'))
        started=time.perf_counter();packets=[]
        data=admission_input(batches,snapshot,settings.resources.market_refresh_seconds)
        try:packets.append(pool.run(key,data,snapshot))
        except (torch.cuda.OutOfMemoryError,MemoryError):
            if device!='auto' or choice['device']=='cpu':raise
            torch.cuda.empty_cache();settings.resources.expert_devices[key]='cpu'
            choice.update(device='cpu',reason='실제 CUDA 작업 메모리가 부족해 CPU로 재검사')
            packets.append(pool.run(key,data,snapshot))
        spec=dict(expert_ids=[key],config=dict(feature_sizes={key:item['feature_size']},
                  stock_policy_ids=[key] if item['role']=='action' else []))
        tokens,mask,_=prepare_evidence({key:packets},packets[0]['symbols'],spec,snapshot['as_of'])
        if not mask.any():raise ValueError('현재 시점에 사용할 수 있는 원본 출력이 없습니다. 입력 날짜와 갱신 상태를 확인하세요.')
        return dict(status='passed',detail='실제 입력·출력 크기·고정 가중치 검사 통과',tested=time.time(),
            package_sha256=reference['sha256'],input_as_of=snapshot['as_of'],output_as_of=packets[0]['as_of'],
            output_shape=packets[0].get('output_shape'),seconds=time.perf_counter()-started,
            sample_output=packets[0],weight_files=sorted(weight_reads),device_choice=choice,metrics={**pool.metrics[key],'device_reason':choice['reason']})
    finally:pool.close();journal.close();settings.resources.expert_devices=original_devices


def apply(settings,header,catalog,active,progress):
    for key in active:
        if key not in catalog['experts']:raise ValueError('라이브러리에 없는 Expert: '+key)
        item=catalog['experts'][key];check=item['check']
        if check.get('status')!='passed' or check.get('package_sha256')!=item['package']['sha256'] or (item.get('conversion') and item['conversion'].get('validation',{}).get('passed') is not True):
            raise ValueError('현재 패키지의 실제 추론 검사를 먼저 통과해야 합니다: '+item['name'])
        package=load_package(settings.resolve(settings.expert_checkpoint),item['package'],verify=True)
        source=(package.get('conversion') or {}).get('source_id')
        if source:header.setdefault('slot_sources',{})[key]=source
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
    elif kind=='search':
        from .expert_discovery import search
        result=search(settings,catalog,payload,progress);catalog['discovery']=result
    elif kind=='acquire':
        from .expert_acquisition import acquire
        from .expert_comparison import compare
        item,baseline=acquire(settings,catalog,payload,progress);catalog['experts'][item['id']]=item
        atomic_json(catalog,catalog_path(settings))
        try:
            item['check']=probe(settings,item,payload.get('device','auto'))
            if baseline:
                result=compare(settings,config,catalog,dict(baseline=baseline,variant=item['id'],device=payload.get('device','auto'),repeats=3),progress)
                catalog['comparison']=result;item['comparison']=result
        except Exception as exc:item['check']=dict(status='failed',detail=str(exc),tested=time.time())
        result=item
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
    elif kind=='probe_all':
        from .expert_inspection import inspect_all
        result=inspect_all(settings,config,catalog,payload,progress)
    elif kind=='probe':
        key=payload.get('id','')
        if key not in catalog['experts']:raise ValueError('등록되지 않은 패키지')
        progress(stage='probing',expert=key,detail='실제 입력으로 추론 검사 중')
        try:catalog['experts'][key]['check']=probe(settings,catalog['experts'][key],payload.get('device','auto'))
        except Exception as exc:catalog['experts'][key]['check']=dict(status='failed',detail=str(exc),tested=time.time())
        if (catalog['experts'][key].get('conversion') or {}).get('validation',{}).get('passed') is False:
            catalog['experts'][key]['check'].update(status='quality_warning',detail='출력 차이 기준 초과 · 동일 입력 비교에서 허용 기준을 확인하세요.')
        result=catalog['experts'][key]['check']
    elif kind=='compare':
        from .expert_comparison import compare
        result=compare(settings,config,catalog,payload,progress)
        catalog['comparison']=result
        item=catalog['experts'][payload['variant']]
        if (item.get('conversion') or {}).get('source_id')==payload['baseline']:
            from .expert_conversion import quality_check
            item['check']=dict(status='passed',detail='동일 실제 입력 추론·출력 검사 통과',tested=time.time(),
                package_sha256=item['package']['sha256'],sample_output=result['variant']['packet'],metrics=result['variant']['metrics'])
            quality_check(item,result,payload)
    elif kind=='convert':
        from .expert_conversion import convert,quality_check
        from .expert_comparison import compare
        item=convert(settings,catalog,payload,progress);slot=item['id']
        catalog['experts'][slot]=item
        # Register first so a failed or interrupted comparison remains visible and removable.
        atomic_json(catalog,catalog_path(settings))
        progress(stage='probing',detail='변환 후보 · 실제 입력 추론 검사')
        try:
            item['check']=probe(settings,item,payload.get('device','auto'))
            catalog['comparison']=compare(settings,config,catalog,dict(baseline=payload['id'],variant=slot,
                device=payload.get('device','auto'),repeats=payload.get('repeats',3)),progress)
            item['conversion']['comparison']=dict(relative_rmse=catalog['comparison']['relative_rmse'],
                speed_ratio=catalog['comparison']['speed_ratio'],input_sha256=catalog['comparison']['input_sha256'])
            quality_check(item,catalog['comparison'],payload)
        except Exception as exc:
            item['check']=dict(status='failed',detail='변환 검사·비교 실패: '+str(exc),tested=time.time())
        result=item
    elif kind=='optimize':
        from .expert_optimizer import optimize
        result=optimize(settings,config,catalog,payload,progress)
    elif kind=='apply':
        result=apply(settings,header,catalog,list(payload.get('active',[])),progress)
        catalog['installed']={k:r['sha256'] for k,r in header['expert_packages'].items()}
        if payload.get('optimizer_base'):
            record=catalog['optimizations'][payload['optimizer_base']]
            record.update(stage='complete',applied=True,finished=time.time());record.pop('target_active',None)
    elif kind=='delete':
        key=payload.get('id','')
        if key not in catalog['experts']:raise ValueError('등록되지 않은 패키지')
        item=catalog['experts'][key];active=[k for k in catalog.get('active',[]) if k!=key]
        header['expert_mapping'].pop(key,None);header['expert_packages'].pop(key,None)
        header.get('slot_sources',{}).pop(key,None)
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
