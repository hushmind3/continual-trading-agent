"""One isolated Expert benchmark on the exact immutable input shared by an A/B test."""
import argparse
import time
import statistics
import torch
from ..state_io import atomic_json,read_json
from .config import load_settings
from .assets import ExpertPool,guard_model_assets
from .observations import prepare_evidence
from .work_devices import choose_device


def run(config,input_path,output_path,key,device,repeats):
    settings=load_settings(config)
    torch.set_num_threads(settings.learning.cpu_threads)
    request=read_json(input_path);item=request['items'][key]
    choice=choose_device(settings,device,item['package']['bytes'],item.get('check',{}).get('metrics',{}).get('peak_vram_bytes',0))
    settings.resources.expert_devices[key]=choice['device']
    reads=guard_model_assets(settings.resolve(settings.expert_checkpoint),[item['package']])
    started=time.perf_counter();pool=ExpertPool(settings,extra_packages={key:item['package']},keep_device=True)
    times=[];packets=[];cold=None
    try:
        for iteration in range(repeats+1):
            lap=time.perf_counter()
            try:packet=pool.run(key,request['input'],request['snapshot'])
            except (torch.cuda.OutOfMemoryError,MemoryError):
                if device!='auto' or choice['device']=='cpu':raise
                torch.cuda.empty_cache();settings.resources.expert_devices[key]='cpu'
                choice.update(device='cpu',reason='실제 CUDA 작업 메모리가 부족해 CPU로 재측정')
                packet=pool.run(key,request['input'],request['snapshot'])
            spec=dict(expert_ids=[key],config=dict(feature_sizes={key:item['feature_size']},stock_policy_ids=[key] if item['role']=='action' else []))
            _,mask,_=prepare_evidence({key:packet},packet['symbols'],spec,request['snapshot']['as_of'],settings.resources.market_refresh_seconds)
            if not mask.any():raise ValueError('같은 실제 입력에서 사용할 수 있는 출력이 없습니다.')
            elapsed=time.perf_counter()-lap
            if not iteration:cold=elapsed
            else:times.append(elapsed)
            packets.append(packet['native_output'])
        atomic_json(dict(id=key,packet=packet,cold_seconds=cold,warm_median_seconds=statistics.median(times),
            warm_min_seconds=min(times),warm_max_seconds=max(times),repeats=repeats,device_choice=choice,metrics={**pool.metrics[key],'device_reason':choice['reason']},
            weight_files=sorted(reads),wall_seconds=time.perf_counter()-started,outputs=packets[1:]),output_path)
    finally:pool.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--input',required=True)
    parser.add_argument('--output',required=True);parser.add_argument('--key',required=True)
    parser.add_argument('--device',choices=['cpu','auto','cuda:0'],default='cpu');parser.add_argument('--repeats',type=int,default=3)
    args=parser.parse_args();run(args.config,args.input,args.output,args.key,args.device,args.repeats)
