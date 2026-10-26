"""Read native engine counters and owned llama.cpp slot counters, without estimating tokens."""
import json
import time
import re
from pathlib import Path
from urllib.request import urlopen


def begin(worker):
    worker._slot_sample = None
    worker._processed_prompt_tokens = 0
    worker._processed_prompt_calls = 0
    worker._cache_reports = []
    # Observe the original engine's raw usage normalization, preserving its result.
    # Canonical zero alone cannot distinguish a reported cache miss from missing data.
    from agent import turn_usage
    from functools import wraps
    current = turn_usage.normalize_usage
    if not getattr(current, '_platform_cache_observer', False):
        @wraps(current)
        def observe(raw, *args, **kwargs):
            result = current(raw, *args, **kwargs)
            def present(path):
                value = raw
                for key in path:
                    value = value.get(key) if isinstance(value, dict) else getattr(value, key, None)
                    if value is None: return False
                return True
            known = any(present(path) for path in (
                ('prompt_tokens_details','cached_tokens'), ('input_tokens_details','cached_tokens'),
                ('cache_read_input_tokens',), ('prompt_cache_hit_tokens',), ('cached_tokens',)))
            worker._cache_reports.append((result.prompt_tokens, result.cache_read_tokens, known))
            return result
        observe._platform_cache_observer = True
        turn_usage.normalize_usage = observe
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
        processed = re.search(r'prompt eval time\s*=.*?/\s*(\d+)\s+tokens', line)
        if processed:
            worker._processed_prompt_tokens = getattr(worker, '_processed_prompt_tokens', 0) + int(processed.group(1))
            worker._processed_prompt_calls = getattr(worker, '_processed_prompt_calls', 0) + 1
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
        metrics['request_input_tokens'] = sum(getattr(item, 'session_prompt_tokens', 0) for item in (agent, speaker) if item) + usage.get('prompt_tokens', usage.get('input_tokens', 0))
        cached = sum(getattr(item, 'session_cache_read_tokens', 0) for item in (agent, speaker) if item) + usage.get('cache_read_tokens', 0)
        if cached:
            metrics['cached_input_tokens'] = cached
            metrics['processed_input_tokens'] = max(0, metrics['request_input_tokens'] - cached)
        reports = getattr(worker, '_cache_reports', [])
        if reports and len(reports) == metrics['api_calls'] and all(row[2] for row in reports) and sum(row[0] for row in reports) == metrics['request_input_tokens']:
            metrics['cached_input_tokens'] = sum(row[1] for row in reports)
            metrics['processed_input_tokens'] = metrics['request_input_tokens'] - metrics['cached_input_tokens']
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
            count = getattr(worker, '_processed_prompt_calls', 0)
            processed = getattr(worker, '_processed_prompt_tokens', 0)
            total = metrics.get('request_input_tokens', 0)
            if count and count == metrics.get('api_calls') and processed <= total:
                metrics['processed_input_tokens'] = processed
                metrics['cached_input_tokens'] = total - processed
        except (OSError, ValueError, TypeError): pass
    metrics['elapsed_seconds']=round(max(0,(worker.job.get('finished_at') or time.time())-worker.job.get('started_at',time.time())),1)
    return metrics


def saved(db, session_id):
    """Use the native session row and metadata; never create another usage DB."""
    tip = db.get_compression_chain(session_id)[-1]
    value = db.get_session_model_config_value(tip, '_platform_runtime_metrics', {}) or db.get_session_model_config_value(session_id, '_platform_runtime_metrics', {}) or {}
    return value.get('last')


def persist(worker):
    session_id = worker.job.get('session_id')
    if not session_id or worker.job.get('application') or not worker.job.get('metrics'): return
    request_id = worker.job.get('owner_request_id')
    previous = saved(worker.db, session_id)
    if previous and previous.get('request_id') == request_id: return
    last = {**worker.job['metrics'], 'model': worker.job.get('model'), 'request_id': request_id,
            'recorded_at': worker.job.get('finished_at') or time.time()}
    worker.db.update_conversation_model_config_value(session_id, '_platform_runtime_metrics',
        lambda value: {'last': last, 'previous': (value or {}).get('last')})
    worker.job['metrics'] = last


def session_metrics(db, session_id):
    metrics = dict(saved(db, session_id) or {})
    rows = [db.get_session(key) or {} for key in db.get_compression_lineage(session_id)]
    total = sum(row.get(key) or 0 for row in rows for key in ('input_tokens', 'cache_read_tokens', 'cache_write_tokens'))
    if total: metrics['cumulative_input_tokens'] = total
    return metrics or None
