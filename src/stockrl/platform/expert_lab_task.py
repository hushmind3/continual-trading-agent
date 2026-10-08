"""One isolated Expert benchmark on the exact immutable input shared by an A/B test."""
import argparse
import time
import statistics
import torch
from ..state_io import atomic_json,read_json
from .config import load_settings
from .assets import ExpertPool,guard_model_assets


def run(config,input_path,output_path,key,device,repeats):
    settings=load_settings(config);settings.resources.expert_devices[key]=device
    torch.set_num_threads(settings.learning.cpu_threads)
    request=read_json(input_path);item=request['items'][key]
    reads=guard_model_assets(settings.resolve(settings.expert_checkpoint),[item['package']])
    started=time.perf_counter();pool=ExpertPool(settings,extra_packages={key:item['package']})
    times=[];packets=[];cold=None
    try:
        for iteration in range(repeats+1):
            lap=time.perf_counter()
            packet=pool.run(key,request['input'],request['snapshot'])
            elapsed=time.perf_counter()-lap
            if not iteration:cold=elapsed
            else:times.append(elapsed)
            packets.append(packet['native_output'])
        atomic_json(dict(id=key,packet=packet,cold_seconds=cold,warm_median_seconds=statistics.median(times),
            warm_min_seconds=min(times),warm_max_seconds=max(times),repeats=repeats,metrics=pool.metrics[key],
            weight_files=sorted(reads),wall_seconds=time.perf_counter()-started,outputs=packets[1:]),output_path)
    finally:pool.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--input',required=True)
    parser.add_argument('--output',required=True);parser.add_argument('--key',required=True)
    parser.add_argument('--device',choices=['cpu','auto','cuda:0'],default='cpu');parser.add_argument('--repeats',type=int,default=3)
    args=parser.parse_args();run(args.config,args.input,args.output,args.key,args.device,args.repeats)
