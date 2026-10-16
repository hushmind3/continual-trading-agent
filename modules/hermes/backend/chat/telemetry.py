"""Read native engine counters and owned llama.cpp slot counters, without estimating tokens."""
import json
import time
from urllib.request import urlopen


def update(worker):
    now=time.monotonic()
    metrics=dict(worker.job.get('metrics') or {})
    agent=worker.agent
    if agent:
        context=getattr(agent,'context_compressor',None)
        for key,attr in [('input_tokens','session_input_tokens'),('output_tokens','session_output_tokens'),('api_calls','session_api_calls')]:
            metrics[key]=getattr(agent,attr,0)
        if context:
            metrics['context_limit']=getattr(context,'context_length',None)
            metrics['context_tokens']=max(0,getattr(context,'last_prompt_tokens',0) or 0) or metrics.get('context_tokens')
    if worker.model_process and worker.model_process.poll() is None and now-getattr(worker,'_slot_checked',0)>.8:
        worker._slot_checked=now
        try:
            with urlopen(worker.model_base.removesuffix('/v1')+'/slots',timeout=.35) as response:
                slots=json.load(response)
            if slots:
                slot=slots[0];decoded=int((slot.get('next_token') or [{}])[0].get('n_decoded') or 0)
                metrics['context_limit']=slot.get('n_ctx')
                metrics['context_tokens']=int(slot.get('n_prompt_tokens') or 0)+decoded
                previous=getattr(worker,'_slot_sample',None)
                if slot.get('is_processing'):
                    if previous and previous[0]==slot.get('id_task') and decoded>previous[1]:
                        metrics['generation_tps']=round((decoded-previous[1])/(now-previous[2]),1)
                    worker._slot_sample=(slot.get('id_task'),decoded,now)
                else:worker._slot_sample=None
        except (OSError,ValueError,TypeError,KeyError):pass
    metrics['elapsed_seconds']=round(max(0,(worker.job.get('finished_at') or time.time())-worker.job.get('started_at',time.time())),1)
    return metrics
