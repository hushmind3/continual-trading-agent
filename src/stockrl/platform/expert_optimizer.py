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


def best_precision(reports,current,goal,ram_total,vram_total,quantization_first=False):
    def pressure(row):
        metrics=row['measurement']['metrics']
        return max((metrics.get('resident_bytes') or row['bytes'])/max(vram_total,1),1e-6) if goal=='memory' else max(metrics.get('peak_ram_bytes',0)/max(ram_total,1),metrics.get('peak_vram_bytes',0)/max(vram_total,1),1e-6)
    reference=next(r for r in reports if r['id']==current)
    seconds=max(reference['measurement']['warm_median_seconds'],1e-6);memory=pressure(reference)
    for row in reports:
        latency=row['measurement']['warm_median_seconds']/seconds;ram=pressure(row)/memory
        row['score']=latency if goal=='speed' else ram if goal=='memory' else .6*latency+.4*ram
        row['eligible']=row['passed']
    eligible=[r for r in reports if r['eligible']]
    if quantization_first:
        compressed=[r for r in eligible if r['precision'].lower().startswith(('nf4','int4','int8','gguf'))]
        if compressed:eligible=compressed
    if not eligible:
        # Preserve quality even when returning to FP32 costs more time than a rejected current variant.
        eligible=[r for r in reports if r['passed']]
    chosen=min(eligible,key=lambda r:(r['score'],r['bytes']))
    if not quantization_first and reference['passed'] and chosen['score']>.95:chosen=reference
    for row in reports:
        row['decision']='selected' if row is chosen else 'rejected' if not row['eligible'] else 'not_selected'
        if row is chosen:
            row['reason']=('기존 버전이 출력 기준을 넘어서 통과한 버전으로 복귀 · 정확도를 우선' if not reference['passed'] else
                '허용 기준을 통과한 최적 후보' if row['id']!=current else '5% 이상 개선되는 적격 후보가 없어 현재 버전 유지')
        elif not row['passed']:row['reason']=row.get('detail','출력 허용 기준 초과')
        elif not row['eligible']:row['reason']=f"현재 버전 대비 추론 시간이 {'50' if goal=='memory' else '15'}% 넘게 증가해 제외"
        elif row['score']>.95 and chosen is reference:row['reason']='현재 버전 대비 목표 점수 개선이 5% 미만'
        else:row['reason']='선택된 버전보다 목표 점수가 높아 미선택 · 낮을수록 유리'
    return chosen


def measurement_summary(value):
    return {key:v for key,v in value.items() if key not in ('packet','outputs','weight_files')}


def optimize(settings,config,catalog,payload,progress):
    payload={'validation_mode':'functional',**payload}
    base=payload.get('id');goal=payload.get('goal','memory')
    if base not in catalog['experts'] or goal not in ('balanced','speed','memory'):raise ValueError('Expert와 최적화 목표를 선택하세요.')
    base=(catalog['experts'][base].get('conversion') or {}).get('source_id') or base
    if base not in catalog['experts']:raise ValueError('정밀도 자동 비교에는 원본 Expert 패키지가 필요합니다.')
    ids=family_ids(catalog,base);active=[k for k in ids if k in catalog.get('active',[])];current=active[0] if active else base
    fixture=capture_input(settings,catalog,base);reports=[];created=[];baseline=None
    record=dict(stage='measuring',goal=goal,input_as_of=fixture['snapshot']['as_of'],reports=[],started=time.time(),
        previous=current,attempts={p:dict(status='pending',detail='아직 검사하지 않음') for p in ('nf4','int4','int8','fp16','bf16')})
    for precision in ('fp16','bf16'):record['attempts'][precision]=dict(status='not_requested',detail='저비트 양자화 정책 · 부동소수점 변환은 자동 선택 대상에서 제외')
    catalog.setdefault('optimizations',{})[base]=record
    def save():atomic_json(catalog,catalog_path(settings))
    def measure(key):
        nonlocal baseline
        result=compare(settings,config,catalog,dict(baseline=base,variant=key,device=payload.get('device','auto'),repeats=1),progress,
            fixture=fixture,baseline_result=baseline)
        baseline=result['baseline'];catalog['comparison']=result
        item=catalog['experts'][key]
        measurement=result['baseline'] if key==base else result['variant']
        item['check']=dict(status='passed',detail='실제 추론·출력 크기·고정 가중치 검사 통과',tested=time.time(),
            package_sha256=item['package']['sha256'],sample_output=measurement['packet'],metrics=measurement['metrics'],seconds=measurement['warm_median_seconds'])
        if item.get('conversion'):quality_check(item,result,payload)
        row=dict(id=key,precision=item['representation'],passed=key==base or item['check']['status']=='passed',
            detail=item['check']['detail'],bytes=item['package']['bytes'],measurement=measurement_summary(measurement),
            relative_rmse=result['relative_rmse'],direction_agreement=result.get('direction_agreement'),action_agreement=result['action_agreement'])
        precision=(item.get('conversion') or {}).get('precision')
        if precision:record['attempts'][precision]=dict(status='measured',id=key,detail=row['detail'])
        reports.append(row);record['reports']=reports;save()
    try:
        measure(current)
        if current!=base:
            item=catalog['experts'][base]
            reports.append(dict(id=base,precision=item['representation'],passed=True,detail='원본 비교 기준',bytes=item['package']['bytes'],measurement=measurement_summary(baseline)))
        for precision in ('nf4','int4','int8'):
            if catalog['experts'][base]['representation'].split(' · ')[0].lower()==precision:
                record['attempts'][precision]=dict(status='native',id=base,detail='원본과 동일한 정밀도 · 별도 변환 불필요');save();continue
            found=next((k for k in ids if (catalog['experts'][k].get('conversion') or {}).get('precision')==precision),None)
            if found==current:continue
            progress(stage='optimizing',detail=precision.upper()+' 후보 생성·검사·측정',expert=base)
            record['attempts'][precision]=dict(status='running',detail='변환·추론·비교 중');save()
            try:
                if found is None:
                    slot=base+'_'+precision;n=2
                    while slot in catalog['experts']:slot=base+'_'+precision+'_'+str(n);n+=1
                    item=convert(settings,catalog,dict(id=base,precision=precision,slot=slot,device=payload.get('device','auto')),progress)
                    found=item['id'];created.append(found);catalog['experts'][found]=item;save()
                measure(found)
            except Exception as exc:
                record['attempts'][precision]=dict(status='failed',id=found,detail=str(exc))
                if found and found in catalog['experts']:
                    catalog['experts'][found]['check']=dict(status='failed',detail=str(exc),tested=time.time())
                record.setdefault('failures',[]).append(dict(precision=precision,detail=str(exc)));save()
        from .resources import ResourceMonitor
        resources=ResourceMonitor(settings.state_dir).snapshot({})
        vram_total=resources['gpu'].get('total_bytes') or (torch.cuda.mem_get_info()[1] if torch.cuda.is_available() else 0)
        selected=best_precision(reports,current,goal,resources['ram_total_bytes'],vram_total,quantization_first=payload.get('quantization_first',True))
        record.update(selected=selected['id'],previous=current,reports=reports,stage='selected')
        if payload.get('quantization_first',True) and not selected['precision'].lower().startswith(('nf4','int4','int8','gguf')):
            record.update(replacement_required=True,detail='정상 실행되는 저비트 버전 없음 · 운영에서 제외 후 다른 Expert 추가')
            if active:record['target_active']=[k for k in catalog['active'] if k not in ids]
        save()
        if active and selected['id']!=current and not record.get('replacement_required'):
            record['target_active']=[k for k in catalog['active'] if k not in ids]+[selected['id']]
        # Retain original, selected, and every version the user had before this run.
        for key in created:
            if key==selected['id']:continue
            recycle(package_path(settings.resolve(settings.expert_checkpoint),catalog['experts'][key]['package']))
            catalog['experts'].pop(key)
        for row in reports:row['package_available']=row['id'] in catalog['experts']
        record.update(stage='deploying' if record.get('target_active') else 'complete',applied=False,finished=time.time(),base=base)
        save();return record
    except Exception as exc:
        record.update(stage='error',error=str(exc));save();raise


def optimize_all(settings,config,catalog,payload,progress):
    bases=list(dict.fromkeys((catalog['experts'][key].get('conversion') or {}).get('source_id') or key for key in catalog.get('active',[])))
    active=list(catalog.get('active',[]));results=[]
    for index,base in enumerate(bases):
        progress(stage='optimizing_all',completed=index,total=len(bases),detail=f'운영 구성 저비트 최적화 {index+1}/{len(bases)} · {catalog["experts"][base]["name"]}')
        if catalog['experts'][base].get('executor')=='llama_cpp':
            results.append(dict(base=base,stage='complete',detail='GGUF 원본 압축 엔진 사용'));continue
        try:
            result=optimize(settings,config,catalog,{**payload,'id':base,'goal':'memory'},lambda **v:progress(**{**v,'completed':index,'total':len(bases)}))
            if result.get('target_active'):
                family=family_ids(catalog,base);active=[k for k in active if k not in family]+([] if result.get('replacement_required') else [result['selected']])
            results.append(dict(base=base,stage=result['stage'],selected=result.get('selected')))
        except Exception as exc:results.append(dict(base=base,stage='error',detail=str(exc)))
    result=dict(base='all',results=results,target_active=active if set(active)!=set(catalog.get('active',[])) else None)
    catalog['optimization_all']=result;return result


def admit_quantized(settings,config,catalog,item,payload,progress):
    if item.get('executor')=='llama_cpp':return item
    result=optimize(settings,config,catalog,{**payload,'id':item['id'],'goal':'memory'},progress)
    if result.get('replacement_required'):
        item['check'].update(status='unsupported',detail='저비트 실행기 검사 실패 · 구성에 추가하지 않음')
        return item
    selected=catalog['experts'][result['selected']]
    if selected['id']!=item['id']:item['check'].update(status='reference_only',detail='양자화 원본 참조 · 운영에서는 저비트 버전 사용')
    return selected
