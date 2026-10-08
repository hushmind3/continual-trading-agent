"""One bounded heavy-Expert job; exit releases model pages and native library caches."""
import argparse
import os
import torch
from ..state_io import atomic_json,read_json
from .assets import ExpertPool,guard_model_assets
from .config import load_settings
from .worker_state import stopped


def run(config,request_path):
    settings=load_settings(config)
    weight_reads=guard_model_assets(settings.resolve(settings.expert_checkpoint))
    torch.set_num_threads(settings.learning.cpu_threads)
    request=read_json(request_path);key=request['key']
    progress=request_path.with_suffix('.progress.json')
    result=request_path.with_suffix('.result.json')
    pool=None
    try:
        pool=ExpertPool(settings,keep_device=True)
        pool.metrics[key]=request.get('metrics',{})
        packets=[]
        for index,data in enumerate(request['batches']):
            if stopped(settings,'experts'):raise InterruptedError('Expert 정지 요청')
            atomic_json(dict(pid=os.getpid(),batch=index+1,batches=len(request['batches'])),progress)
            packets.append(pool.run(key,data,{}))
        pool.metrics[key]['weight_files']=sorted(weight_reads)
        atomic_json(dict(packets=packets,metrics=pool.metrics[key]),result)
    except Exception as exc:
        status='waiting_resources' if isinstance(exc,MemoryError) else 'needs_input' if isinstance(exc,ValueError) else 'error'
        atomic_json(dict(error=f'{type(exc).__name__}: {exc}',status=status),result)
        raise
    finally:
        if pool:pool.close()


if __name__=='__main__':
    from pathlib import Path
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--job',type=Path,required=True)
    args=parser.parse_args();run(args.config,args.job)
