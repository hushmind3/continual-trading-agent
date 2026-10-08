"""Output/latency/resource comparison; never executes orders or updates a model."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import numpy as np
from ..state_io import atomic_json,read_json
from ..market_reader import IncrementalMarketCSV
from .journal import Journal
from .expert_packages import load_package
from .expert_inputs import snapshot_for


def compare(settings,config,catalog,payload,progress):
    ids=[payload.get('baseline'),payload.get('variant')]
    if any(k not in catalog['experts'] for k in ids):raise ValueError('비교할 두 Expert를 선택하세요.')
    items={k:catalog['experts'][k] for k in ids};base,variant=[items[k] for k in ids]
    if base['input']!=variant['input'] or base['feature_size']!=variant['feature_size'] or base['role']!=variant['role']:
        raise ValueError('동일한 입력 계약·학습 종목·출력 크기의 모델을 비교하세요.')
    repeats=int(payload.get('repeats',3))
    if not 1<=repeats<=10:raise ValueError('반복 횟수는 1~10회입니다.')
    device=payload.get('device','cpu')
    if device not in ('cpu','auto','cuda:0'):raise ValueError('실행 장치를 선택하세요.')
    package=load_package(settings.resolve(settings.expert_checkpoint),base['package'],verify=True)
    reader=IncrementalMarketCSV(settings.state_dir/'live'/'market.csv',retain_timestamps=256);frame,_=reader.refresh()
    if frame is None or frame.empty:raise ValueError('실제 입력 시세가 필요합니다.')
    journal=Journal(settings.state_dir/'operations.sqlite3')
    try:batches,snapshot=snapshot_for(package['entry'],frame,journal,reader.path.with_name('timeframes.sqlite3'))
    finally:journal.close()
    data={'input':batches[0],'snapshot':snapshot,'items':items}
    canonical=json.dumps(data,sort_keys=True,default=str).encode();results=[]
    with tempfile.TemporaryDirectory(prefix='stockrl-expert-comparison-') as directory:
        source=Path(directory)/'input.json';atomic_json(data,source,default=lambda x:x.isoformat() if hasattr(x,'isoformat') else x.item())
        for index,key in enumerate(ids):
            progress(stage='benchmark',completed=index,total=2,detail=items[key]['name']+' 동일 입력 측정 중')
            target=Path(directory)/('result-'+str(index)+'.json')
            process=subprocess.run([sys.executable,'-m','stockrl.platform.expert_lab_task','--config',str(config),
                '--input',str(source),'--output',str(target),'--key',key,'--device',device,'--repeats',str(repeats)],
                capture_output=True,text=True,encoding='utf8',timeout=settings.resources.inference_timeout_seconds*(repeats+1),
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if process.returncode:raise ValueError('모델 측정 실패: '+process.stderr[-2000:])
            results.append(read_json(target))
    a,b=[np.asarray(r['packet']['native_output'],float) for r in results]
    if a.shape!=b.shape or results[0]['packet']['symbols']!=results[1]['packet']['symbols']:
        raise ValueError('비교 출력의 종목 순서 또는 크기가 다릅니다.')
    delta=b-a;agreement=None
    if base['role']=='action':agreement=float(np.mean(a[...,:3].argmax(-1)==b[...,:3].argmax(-1)))
    return dict(baseline=results[0],variant=results[1],input_as_of=snapshot['as_of'],input_sha256=hashlib.sha256(canonical).hexdigest(),
        symbols=results[0]['packet']['symbols'],mean_absolute_error=float(np.abs(delta).mean()),
        max_absolute_error=float(np.abs(delta).max()),rmse=float(np.sqrt(np.mean(delta**2))),
        relative_rmse=float(np.linalg.norm(delta)/max(np.linalg.norm(a),1e-12)),action_agreement=agreement,
        speed_ratio=results[0]['warm_median_seconds']/max(results[1]['warm_median_seconds'],1e-12),
        file_bytes={k:items[k]['package']['bytes'] for k in ids},account_changed=False,model_trained=False,
        scope='동일한 실제 입력의 출력·지연·자원 비교이며 매매 수익 성능을 보장하지 않습니다.')
