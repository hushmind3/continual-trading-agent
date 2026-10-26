"""Measure the owned idle llama.cpp directly, without Hermes or a thinking template."""
import json
from pathlib import Path
import threading
import time
import urllib.request
import psutil

ROOT=Path(__file__).resolve().parents[5]
OUTPUT=ROOT/'runtime/ai_agent/choki/verification/performance'

def request(url,payload=None):
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=100) as response:return json.load(response)

def main():
    state=request('http://127.0.0.1:8766/api',{'operation':'ai_agent/choki/status','payload':{}})
    if state['job'].get('state') in ('starting','running','stopping'):raise RuntimeError('Hermes is busy')
    base=state['local_model']['base_url'].removesuffix('/v1')
    props=request(base+'/props')
    model=next(p for p in psutil.process_iter(['name','cmdline']) if p.info['name']=='llama-server.exe' and '--port' in p.info['cmdline'] and base.endswith(':'+p.info['cmdline'][p.info['cmdline'].index('--port')+1]))
    samples=[];done=threading.Event();model.cpu_percent()
    def monitor():
        while not done.wait(.5):samples.append(model.cpu_percent())
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    started=time.monotonic()
    try:
        result=request(base+'/completion',{'prompt':'Complete the ascending list with numbers separated by commas: 1, 2, 3, 4,','n_predict':64,'temperature':0,'seed':42,'ignore_eos':True,'cache_prompt':False})
    finally:done.set();thread.join(2)
    evidence={'context_limit':props['default_generation_settings']['n_ctx'],'wall_seconds':round(time.monotonic()-started,3),
        'timings':result.get('timings'),'predicted':result.get('tokens_predicted'),'evaluated':result.get('tokens_evaluated'),
        'hermes_used':False,'chat_template_used':False,'cpu_percent_samples':samples}
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT/'direct-generation.json').write_text(json.dumps(evidence,indent=2),encoding='utf8')
    print(json.dumps(evidence))

if __name__=='__main__':main()
