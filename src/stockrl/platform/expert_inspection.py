"""Inspect every installed version; failures are local and never change selection."""
import time
from ..state_io import atomic_json
from .library_store import catalog_path
from .expert_comparison import capture_input,measure,comparison_result
from .expert_conversion import quality_check


def inspect_all(settings,config,catalog,payload,progress):
    items=catalog['experts'];reports=[];fixtures={};baselines={}
    ordered=sorted(items,key=lambda key:(bool(items[key].get('conversion')),key))
    record=dict(started=time.time(),total=len(ordered),completed=0,reports=reports)
    catalog['inspection']=record
    for index,key in enumerate(ordered):
        item=items[key];source=(item.get('conversion') or {}).get('source_id',key)
        progress(stage='inspecting_all',completed=index,total=len(ordered),expert=key,
            detail=f"전체 검사 {index+1}/{len(ordered)} · {item['name']} · 입력·무결성·추론·자원·출력 차이")
        try:
            if not item['input']['supported']:raise ValueError(item['input'].get('reason','지원하는 입력 생성기가 없습니다.'))
            if source not in items:raise ValueError('출력 차이를 비교할 원본 패키지가 없습니다.')
            if source not in fixtures:fixtures[source]=capture_input(settings,catalog,source)
            measurement=measure(settings,config,{key:item},fixtures[source],key,payload.get('device','auto'))
            item['check']=dict(status='passed',detail='입력·무결성·출력·추론 3회·RAM/VRAM 검사 통과',tested=time.time(),
                package_sha256=item['package']['sha256'],metrics=measurement['metrics'],sample_output=measurement['packet'],
                seconds=measurement['warm_median_seconds'],input_as_of=fixtures[source]['snapshot']['as_of'])
            if item.get('conversion'):
                if source not in baselines:raise ValueError('원본 검사 실패로 정밀도 출력 차이를 검증할 수 없습니다.')
                if any(item[field]!=items[source][field] for field in ('input','feature_size','role')):raise ValueError('원본과 입력·출력 계약이 다릅니다.')
                result=comparison_result(items,[baselines[source],measurement],fixtures[source])
                previous=item['conversion'].get('validation') or {}
                quality_check(item,result,{'validation_mode':previous.get('mode','reference'),**{k:previous[k] for k in ('max_relative_rmse','min_action_agreement') if k in previous}})
            else:baselines[source]=measurement
        except Exception as exc:
            item['check']=dict(status='failed',detail=str(exc),tested=time.time())
        reports.append(dict(id=key,name=item['name'],status=item['check']['status'],detail=item['check']['detail']))
        record['completed']=index+1;atomic_json(catalog,catalog_path(settings))
        progress(completed=index+1,total=len(ordered))
    record.update(finished=time.time(),passed=sum(r['status']=='passed' for r in reports),
        failed=sum(r['status']=='failed' for r in reports),quality_warning=sum(r['status']=='quality_warning' for r in reports))
    return record
