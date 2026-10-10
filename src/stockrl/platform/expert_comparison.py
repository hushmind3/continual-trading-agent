"""Existing Frozen Expert comparison/selection functions restored from f153957."""
import json,hashlib
import numpy as np

def measure(runtime,key,fixture,repeats=1):
    """Recovered cold/warm measurement loop, using the current input adapter."""
    import statistics,time
    times=[];outputs=[];cold=None
    for iteration in range(repeats+1):
        lap=time.perf_counter();value=runtime.infer(key,fixture);elapsed=time.perf_counter()-lap
        if not iteration:cold=elapsed
        else:times.append(elapsed);outputs.append(value['packet']['native_output'])
    return {'id':key,**value,'cold_seconds':cold,'warm_median_seconds':statistics.median(times),
        'warm_min_seconds':min(times),'warm_max_seconds':max(times),'repeats':repeats,'outputs':outputs}

def forecast_directions(packet,data):
    values=np.asarray(packet['native_output'],float)
    if packet['layout']=='nine_quantiles,batch,variate,horizon':values=values[:,0].transpose(1,0,2)
    values=values.reshape(len(packet['symbols']),-1)
    if packet['layout']=='symbol,direction_confidence_risk':return np.sign(values[:,0])
    point=values[:,0] if 'point_and_nine_quantiles' in packet['layout'] else values[:,3] if 'OHLCV_amount' in packet['layout'] else np.median(values,axis=1)
    if packet['units']=='daily_excess_return':reference=np.zeros(len(point))
    elif data and data.get('series'):reference=np.asarray([row[-1] for row in data['series']])
    elif data and data.get('bars'):reference=np.asarray([row[-1]['close'] for row in data['bars']])
    else:return None
    return np.sign(point-reference)

def comparison_result(items,results,fixture):
    base=items[results[0]['id']];ids=[r['id'] for r in results]
    canonical=json.dumps(fixture,sort_keys=True,default=str).encode()
    a,b=[np.asarray(r['packet']['native_output'],float) for r in results]
    if a.shape!=b.shape or results[0]['packet']['symbols']!=results[1]['packet']['symbols']:
        raise ValueError('비교 출력의 종목 순서 또는 크기가 다릅니다.')
    delta=b-a;agreement=None;direction=None
    if base['role']=='action':agreement=float(np.mean(a[...,:3].argmax(-1)==b[...,:3].argmax(-1)))
    else:
        directions=[forecast_directions(r['packet'],fixture['input']) for r in results]
        if all(d is not None for d in directions):direction=float(np.mean(directions[0]==directions[1]))
    return dict(baseline=results[0],variant=results[1],input_as_of=fixture['snapshot']['as_of'],input_sha256=hashlib.sha256(canonical).hexdigest(),
        symbols=results[0]['packet']['symbols'],mean_absolute_error=float(np.abs(delta).mean()),
        max_absolute_error=float(np.abs(delta).max()),rmse=float(np.sqrt(np.mean(delta**2))),
        relative_rmse=float(np.linalg.norm(delta)/max(np.linalg.norm(a),1e-12)),action_agreement=agreement,direction_agreement=direction,
        speed_ratio=results[0]['warm_median_seconds']/max(results[1]['warm_median_seconds'],1e-12) if results[0]['metrics']['device']==results[1]['metrics']['device'] else None,
        file_bytes={k:items[k]['package']['bytes'] for k in ids},account_changed=False,model_trained=False,
        scope='동일한 실제 입력의 출력·지연·자원 비교이며 매매 수익 성능을 보장하지 않습니다.'+
              (' 가용 자원에 따라 두 모델의 실행 장치가 다릅니다.' if results[0]['metrics']['device']!=results[1]['metrics']['device'] else ''))
