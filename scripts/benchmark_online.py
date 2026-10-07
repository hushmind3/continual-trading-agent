"""Isolated baseline/current benchmarks. Prints measurements; no operational writes."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import numpy as np
import psutil
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]


def baseline_module(name,revision):
    source=subprocess.check_output(['git','show',f'{revision}:src/stockrl/{name}.py'],cwd=ROOT).decode('utf-8')
    module=types.ModuleType('stockrl._baseline_'+name);module.__package__='stockrl'
    exec(compile(source,f'{revision}:{name}','exec'),module.__dict__)
    return module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision',help='measure a trusted local git baseline without checking it out')
    parser.add_argument('--native',action='store_true',help='actual mmap model load + original TimesFM and MacroHFT GPU inference')
    parser.add_argument('--inputs',action='store_true',help='actual completed Feed input preparation, no trading')
    parser.add_argument('--compare-inputs',action='store_true',help='paired old/current preprocessing on identical frozen Feed and daily data')
    parser.add_argument('--live',action='store_true',help='all applicable original Experts on actual completed Feed, no orders')
    parser.add_argument('--stress-seconds',type=int,help='isolated synthetic CPU learner/inference contention test')
    args=parser.parse_args()
    torch.set_num_threads(4);torch.manual_seed(0)
    process=psutil.Process()
    from stockrl.trading_moe import TradingMoE
    Model=baseline_module('trading_moe',args.revision).TradingMoE if args.revision else TradingMoE
    if args.live:
        from stockrl.paths import TRADING_MOE_CHECKPOINT,default_runtime_dir
        from stockrl.moe_live import LiveInputStream,live_snapshot
        from stockrl.paper_account import PaperAccount
        started=time.perf_counter();model,_=Model.load_checkpoint(TRADING_MOE_CHECKPOINT)
        model.set_learning_device('cuda:0');load=time.perf_counter()-started
        market=default_runtime_dir()/'live/market.csv';frame,stamp=LiveInputStream(market).next_frame()
        started=time.perf_counter();_,_,snapshot,account=live_snapshot(model,market,frame,stamp,PaperAccount.in_memory(.001,.0001))
        prepare=time.perf_counter()-started
        print(json.dumps(dict(stage='prepared',symbols=len(snapshot['symbols']),load_seconds=load,prepare_seconds=prepare)),flush=True)
        started=time.perf_counter()
        with torch.no_grad():decision,_=model(snapshot,torch.as_tensor(account,dtype=torch.float32),device='cuda:0')
        print(json.dumps(dict(scope='actual Feed to all applicable native Experts and controller; no orders/learning',
            timestamp=str(stamp),inference_seconds=time.perf_counter()-started,used_experts=decision['used_experts'],
            blocked=decision['unavailable_stock_policies'],paper_executable=decision['trading_output']['paper_executable'],
            peak_rss_mib=process.memory_info().peak_wset/2**20,resources=model.resources.snapshot())),flush=True)
        return
    if args.inputs or args.compare_inputs:
        from stockrl.paths import TRADING_MOE_CHECKPOINT,default_runtime_dir
        from stockrl.moe_live import LiveInputStream,live_snapshot
        from stockrl.market_panel import GlobalMarketPanel
        from stockrl.paper_account import PaperAccount
        market=default_runtime_dir()/'live'/'market.csv'
        item=LiveInputStream(market).next_frame()
        if item is None:raise RuntimeError('actual completed Feed input unavailable')
        frame,stamp=item;model,_=Model.load_checkpoint(TRADING_MOE_CHECKPOINT,cached_market=True)
        if args.revision:
            legacy_live=baseline_module('moe_live',args.revision)
            legacy_live.GlobalMarketPanel=baseline_module('market_panel',args.revision).GlobalMarketPanel
            snapshot_fn=legacy_live.live_snapshot
        else:snapshot_fn=live_snapshot
        account=PaperAccount.in_memory(.001,.0001);times=[]
        if args.compare_inputs:
            from stockrl.moe_live import daily_history
            daily=daily_history(market,stamp)
            old=baseline_module('moe_live','72d213b');old.GlobalMarketPanel=baseline_module('market_panel','72d213b').GlobalMarketPanel
            measured={}
            for label,fn in [('baseline',old.live_snapshot),('target',live_snapshot)]:
                values=[]
                for _ in range(3):
                    started=time.perf_counter()
                    if label=='baseline':fn(model,market,frame,stamp,account,daily_frame=daily)
                    panel=GlobalMarketPanel(market,raw_frame=frame) if label=='target' else None
                    _,_,snapshot,_=fn(model,market,frame,stamp,account,daily_frame=daily,**({'panel':panel} if panel else {}))
                    values.append(time.perf_counter()-started)
                measured[label+'_p50_ms']=float(np.median(values))*1000
            print(json.dumps(dict(scope='paired identical completed Feed frame and completed daily data; no trading',
                symbols=len(snapshot['symbols']),timestamp=str(stamp),**measured)))
            return
        for _ in range(3):
            started=time.perf_counter()
            if args.revision:snapshot_fn(model,market,frame,stamp,account)
            panel=GlobalMarketPanel(market,raw_frame=frame) if not args.revision else None
            _,_,snapshot,_=snapshot_fn(model,market,frame,stamp,account,**({'panel':panel} if panel else {}))
            times.append(time.perf_counter()-started)
        print(json.dumps(dict(scope='actual completed live Feed preprocessing, same immutable input/account',
            revision=args.revision or 'working-tree',symbols=len(snapshot['symbols']),source_timestamp=str(stamp),
            input_preparation_p50_ms=float(np.median(times))*1000,rss_mib=process.memory_info().rss/2**20)))
        return
    if args.native:
        from stockrl.paths import TRADING_MOE_CHECKPOINT,GPU_OWNER_LOCK
        from stockrl.expert_system import registry_owner
        with registry_owner(GPU_OWNER_LOCK):
            started=time.perf_counter();model,_=Model.load_checkpoint(TRADING_MOE_CHECKPOINT)
            load=time.perf_counter()-started;native=[]
            for key in ('timesfm','macrophft_slope_1'):
                data=dict(model.metadata['construction_inputs'][key]);data['variant']=model.experts[key].entry.get('variant')
                torch.cuda.reset_peak_memory_stats();latencies=[]
                for _ in range(3):
                    started=time.perf_counter();packet=model.experts[key](model.root,data,'cuda:0')
                    torch.cuda.synchronize();latencies.append(time.perf_counter()-started)
                native.append(dict(expert=key,cold_seconds=latencies[0],warm_p50_ms=float(np.median(latencies[1:]))*1000,
                    peak_vram_mib=torch.cuda.max_memory_allocated()/2**20,shape=packet['output_shape']))
                torch.cuda.empty_cache()
            print(json.dumps(dict(scope='actual original native models; recorded source inputs, not live profit test',
                revision=args.revision or 'working-tree',load_seconds=load,native=native,
                rss_mib=process.memory_info().rss/2**20,peak_rss_mib=process.memory_info().peak_wset/2**20)))
        return
    from test_integration_v1 import fixture_model
    from test_online_learning import record
    from stockrl.moe_training import update_batch
    from stockrl.moe_promotion import save_runtime_state
    from stockrl.replay_store import GlobalReplayBuffer
    legacy=baseline_module('moe_training',args.revision) if args.revision else None
    with tempfile.TemporaryDirectory() as directory:
        started=time.perf_counter();template=fixture_model(directory)
        model=Model(dict(template.experts.items()),template.config,template.metadata,directory)
        load=time.perf_counter()-started;optimizer=torch.optim.AdamW(model.parameter_groups(),lr=1e-4)
        if args.stress_seconds:
            if args.revision:raise ValueError('stress mode measures the asynchronous target only')
            from stockrl.moe_learner import AsyncLearner
            from stockrl.operating_rules import operating_rules
            learner=AsyncLearner(model,optimizer,operating_rules());latencies=[];updates=0;contexts=0
            started=time.perf_counter();before=process.memory_info().rss
            try:
                while time.perf_counter()-started<args.stress_seconds:
                    completed=learner.poll(model,optimizer)
                    if completed:updates+=1;contexts+=completed[0]['contexts']
                    tick=time.perf_counter();sample=record(model);latencies.append(time.perf_counter()-tick)
                    if len(latencies)>10000:latencies=latencies[-10000:]
                    if not learner.busy:learner.submit([sample]*32)
                completed=learner.poll(model,optimizer,wait=True)
                if completed:updates+=1;contexts+=completed[0]['contexts']
                print(json.dumps(dict(scope='synthetic fixture concurrent CPU learning/inference; no operational data',
                    seconds=time.perf_counter()-started,inference_samples=len(latencies),updates=updates,contexts=contexts,
                    inference_p50_ms=float(np.median(latencies))*1000,inference_p95_ms=float(np.quantile(latencies,.95))*1000,
                    rss_growth_mib=(process.memory_info().rss-before)/2**20,peak_rss_mib=process.memory_info().peak_wset/2**20,
                    error=learner.error,queue=learner.stats['queue'])))
            finally:learner.close()
            return
        sample=record(model);exp,snapshot,decision=sample;latencies=[]
        for i in range(40):
            started=time.perf_counter()
            with torch.no_grad():model(snapshot,torch.zeros(1,1,16),packets=decision['raw_outputs'])
            if i>=5:latencies.append(time.perf_counter()-started)
        before=process.cpu_times();started=time.perf_counter()
        if legacy:
            for _ in range(32):legacy.update_controller(model,optimizer,exp,snapshot,decision['raw_outputs'],{'AAPL':.4},{'USD':.6},{'AAPL':'BUY'})
        else:update_batch(model,optimizer,[sample]*32)
        training=time.perf_counter()-started;cpu=process.cpu_times()
        checkpoint=Path(directory)/'fixture.pt';model.save_checkpoint(checkpoint)
        started=time.perf_counter();path=save_runtime_state(model,optimizer,checkpoint);saving=time.perf_counter()-started
        replay=GlobalReplayBuffer(journal_path=Path(directory)/'replay.sqlite3',dual_learning=False)
        started=time.perf_counter()
        for i in range(128):exp.timestamp=str(i);replay.add(exp)
        write=time.perf_counter()-started;started=time.perf_counter();replay.pending_batch(128);read=time.perf_counter()-started
        print(json.dumps(dict(scope='1 symbol / 2 expert contracts / CPU4 / 32 contexts',revision=args.revision or 'working-tree',
            model_load_ms=load*1000,inference_p50_ms=float(np.median(latencies))*1000,
            inference_p95_ms=float(np.quantile(latencies,.95))*1000,contexts_per_second=32/training,
            optimizer_steps=model.optimizer_updates,training_wall_seconds=training,
            training_cpu_seconds=cpu.user+cpu.system-before.user-before.system,
            rss_mib=process.memory_info().rss/2**20,peak_rss_mib=process.memory_info().peak_wset/2**20,
            checkpoint_ms=saving*1000,checkpoint_kib=path.stat().st_size/1024,
            replay_write_rows_per_second=128/write,replay_read_rows_per_second=128/read)))


if __name__=='__main__':main()
