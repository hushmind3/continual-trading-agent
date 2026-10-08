"""Measured precision selection, with explicit quality gates and checkpointed replacement."""
import time
import torch
from ..state_io import atomic_json
from .expert_conversion import convert,quality_check
from .expert_comparison import compare,capture_input
from .expert_packages import package_path
from .library_store import catalog_path
from .package_disposal import recycle


def family_ids(catalog,base):
    return [k for k,v in catalog['experts'].items() if k==base or (v.get('conversion') or {}).get('source_id')==base]


def best_precision(reports,current,goal,ram_total,vram_total):
    def pressure(row):
        metrics=row['measurement']['metrics']
        return max(metrics.get('peak_ram_bytes',0)/max(ram_total,1),metrics.get('peak_vram_bytes',0)/max(vram_total,1),1e-6)
    reference=next(r for r in reports if r['id']==current)
    seconds=max(reference['measurement']['warm_median_seconds'],1e-6);memory=pressure(reference)
    for row in reports:
        latency=row['measurement']['warm_median_seconds']/seconds;ram=pressure(row)/memory
        row['score']=latency if goal=='speed' else ram if goal=='memory' else .6*latency+.4*ram
        row['eligible']=row['passed'] and (goal!='memory' or latency<=1.5) and (goal!='balanced' or latency<=1.15)
    eligible=[r for r in reports if r['eligible']]
    if not eligible:
        # Preserve quality even when returning to FP32 costs more time than a rejected current variant.
        eligible=[r for r in reports if r['passed']]
    chosen=min(eligible,key=lambda r:(r['score'],r['bytes']))
    if reference['passed'] and chosen['score']>.95:return reference
    return chosen


def optimize(settings,config,catalog,payload,progress):
    base=payload.get('id');goal=payload.get('goal','balanced')
    if base not in catalog['experts'] or goal not in ('balanced','speed','memory'):raise ValueError('Expert와 최적화 목표를 선택하세요.')
    base=(catalog['experts'][base].get('conversion') or {}).get('source_id') or base
    if base not in catalog['experts']:raise ValueError('정밀도 자동 비교에는 원본 Expert 패키지가 필요합니다.')
    ids=family_ids(catalog,base);active=[k for k in ids if k in catalog.get('active',[])];current=active[0] if active else base
    fixture=capture_input(settings,catalog,base);reports=[];created=[];baseline=None
    record=dict(stage='measuring',goal=goal,input_as_of=fixture['snapshot']['as_of'],reports=[])
    catalog.setdefault('optimizations',{})[base]=record
    def save():atomic_json(catalog,catalog_path(settings))
    def measure(key):
        nonlocal baseline
        result=compare(settings,config,catalog,dict(baseline=base,variant=key,device=payload.get('device','auto'),repeats=3),progress,
            fixture=fixture,baseline_result=baseline)
        baseline=result['baseline'];catalog['comparison']=result
        item=catalog['experts'][key]
        if item.get('conversion'):
            item['check']=dict(status='passed',detail='실제 추론·출력 크기·고정 가중치 검사 통과',tested=time.time(),
                package_sha256=item['package']['sha256'],sample_output=result['variant']['packet'],metrics=result['variant']['metrics'])
            quality_check(item,result,payload)
        measurement=result['baseline'] if key==base else result['variant']
        row=dict(id=key,precision=item['representation'],passed=key==base or item['check']['status']=='passed',
            detail=item['check']['detail'],bytes=item['package']['bytes'],measurement=measurement,
            relative_rmse=result['relative_rmse'],direction_agreement=result.get('direction_agreement'),action_agreement=result['action_agreement'])
        reports.append(row);record['reports']=reports;save()
    try:
        measure(current)
        if current!=base:
            item=catalog['experts'][base]
            reports.append(dict(id=base,precision=item['representation'],passed=True,detail='원본 비교 기준',bytes=item['package']['bytes'],measurement=baseline))
        for precision in ('fp16','bf16','int8','int4'):
            found=next((k for k in ids if (catalog['experts'][k].get('conversion') or {}).get('precision')==precision),None)
            if found==current:continue
            progress(stage='optimizing',detail=precision.upper()+' 후보 생성·검사·측정',expert=base)
            try:
                if found is None:
                    slot=base+'_'+precision;n=2
                    while slot in catalog['experts']:slot=base+'_'+precision+'_'+str(n);n+=1
                    item=convert(settings,catalog,dict(id=base,precision=precision,slot=slot,device=payload.get('device','auto')),progress)
                    found=item['id'];created.append(found);catalog['experts'][found]=item;save()
                measure(found)
            except Exception as exc:
                record.setdefault('failures',[]).append(dict(precision=precision,detail=str(exc)));save()
        from .resources import ResourceMonitor
        resources=ResourceMonitor(settings.state_dir).snapshot({})
        vram_total=resources['gpu'].get('total_bytes') or (torch.cuda.mem_get_info()[1] if torch.cuda.is_available() else 0)
        selected=best_precision(reports,current,goal,resources['ram_total_bytes'],vram_total)
        record.update(selected=selected['id'],previous=current,reports=reports,stage='selected')
        save()
        if active and selected['id']!=current:
            record['target_active']=[k for k in catalog['active'] if k not in ids]+[selected['id']]
        # Retain original, selected, and every version the user had before this run.
        for key in created:
            if key==selected['id']:continue
            recycle(package_path(settings.resolve(settings.expert_checkpoint),catalog['experts'][key]['package']))
            catalog['experts'].pop(key)
        record.update(stage='deploying' if record.get('target_active') else 'complete',applied=False,finished=time.time(),base=base)
        save();return record
    except Exception as exc:
        record.update(stage='error',error=str(exc));save();raise
