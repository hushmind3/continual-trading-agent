"""Identify the memory/offload bottleneck, always restoring the user's model connection."""
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.request
import psutil

ROOT=Path(__file__).resolve().parents[5]
OUTPUT=ROOT/'runtime/ai_agent/choki/verification/performance'
MODEL=''

def request(url,payload=None):
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=90) as response:return json.load(response)

def api(operation,payload=None):
    return request('http://127.0.0.1:8766/api',{'operation':'ai_agent/choki/'+operation,'payload':payload or {}})

def profile(original,context):
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    command=list(original)
    command[command.index('--port')+1]=str(port)
    command[command.index('--ctx-size')+1]=str(context)
    command+=['--log-verbosity','5']
    path=OUTPUT/f'allocation-{context}.log'
    with path.open('wb') as log:
        child=subprocess.Popen(command,cwd=Path(MODEL).parent,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            base=f'http://127.0.0.1:{port}'
            deadline=time.monotonic()+55
            while time.monotonic()<deadline:
                if child.poll() is not None:raise RuntimeError('Diagnostic loader failed: '+str(path))
                try:
                    if request(base+'/health').get('status')=='ok':break
                except Exception:time.sleep(.2)
            else:raise RuntimeError('Diagnostic model not ready')
            props=request(base+'/props')
            result=request(base+'/completion',{'prompt':'Complete the ascending list with numbers separated by commas: 1, 2, 3, 4,','n_predict':64,'temperature':0,'seed':42,'ignore_eos':True,'cache_prompt':False})
            return {'context':props['default_generation_settings']['n_ctx'],'timings':result.get('timings')}
        finally:
            child.terminate()
            try:child.wait(timeout=8)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)

def main():
    global MODEL
    state=api('status')
    if state['job'].get('state') in ('starting','running','stopping'):raise RuntimeError('Hermes is busy')
    base=state['local_model']['base_url'].removesuffix('/v1')
    original=next(p.cmdline() for p in psutil.process_iter(['name']) if p.info['name']=='llama-server.exe' and base.endswith(':'+p.cmdline()[p.cmdline().index('--port')+1]))
    MODEL=original[original.index('--model')+1]
    OUTPUT.mkdir(parents=True,exist_ok=True)
    report={'original_command':original,'profiles':[],'restored':False}
    api('model/unload')
    try:
        for context in (262144,65536):
            result=profile(original,context)
            lines=(OUTPUT/f'allocation-{context}.log').read_text(encoding='utf8',errors='replace').splitlines()
            result['allocation']=[line for line in lines if re.search(r'offload|buffer size|fit_params|n_gpu_layers|n_ctx\s+=|n_layer\s+=',line) and 'slot decode' not in line][-28:]
            report['profiles'].append(result)
            print(json.dumps(result),flush=True)
    finally:
        api('model/load',{'path':MODEL})
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            restored=api('status')
            if restored.get('local_model',{}).get('state')=='ready':report['restored']=True;break
            time.sleep(.25)
        (OUTPUT/'allocation-comparison.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        print('Original settings/model restored:',report['restored'],flush=True)
        if not report['restored']:raise RuntimeError('Original model did not become ready')

if __name__=='__main__':main()
