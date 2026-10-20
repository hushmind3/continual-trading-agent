"""Read native engine counters and owned llama.cpp slot counters, without estimating tokens."""
import json
import time
import re
from pathlib import Path
from urllib.request import urlopen


def begin(worker):
    worker._slot_sample = None
    worker._timing_remainder = ''
    log = getattr(worker, 'model_log', None)
    worker._timing_path = Path(log.name) if log else None
    worker._timing_offset = worker._timing_path.stat().st_size if worker._timing_path and worker._timing_path.is_file() else 0


def local_timing(worker):
    path = getattr(worker, '_timing_path', None)
    if not path or not path.is_file(): return None
    with path.open('rb') as stream:
        stream.seek(worker._timing_offset)
        text = worker._timing_remainder + stream.read(65536).decode('utf-8', errors='replace')
        worker._timing_offset = stream.tell()
    lines = text.split('\n'); worker._timing_remainder = lines.pop()
    rate = None
    for line in lines:
        match = re.search(r'\|\s*(?:eval time\s*=.*?,\s*([0-9.]+)\s+tokens per second\)|n_gen\s*=.*?tg\s*=\s*([0-9.]+)\s+t/s)', line)
        if match: rate = float(match.group(1) or match.group(2))
    return round(rate, 1) if rate is not None else None


def update(worker):
    now=time.monotonic()
    metrics=dict(worker.job.get('metrics') or {})
    agent=worker.agent
    if agent:
        speaker=getattr(worker,'meeting_agent',None)
        usage=worker.job.get('meeting_usage') or {}
        context=getattr(speaker or agent,'context_compressor',None)
        for key,attr in [('input_tokens','session_input_tokens'),('output_tokens','session_output_tokens'),('api_calls','session_api_calls')]:
            metrics[key]=getattr(agent,attr,0)+usage.get(key,0)+(getattr(speaker,attr,0) if speaker else 0)
        if context:
            metrics['context_limit']=getattr(context,'context_length',None)
            metrics['context_tokens']=max(0,getattr(context,'last_prompt_tokens',0) or 0) or metrics.get('context_tokens')
    local = worker.job.get('local_inference', True)
    if local and worker.model_process and worker.model_process.poll() is None and now-getattr(worker,'_slot_checked',0)>.8:
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
    if local and worker.model_process and worker.model_process.poll() is None:
        try:
            rate = local_timing(worker)
            if rate is not None: metrics['generation_tps'] = rate
        except (OSError, ValueError, TypeError): pass
    metrics['elapsed_seconds']=round(max(0,(worker.job.get('finished_at') or time.time())-worker.job.get('started_at',time.time())),1)
    return metrics
