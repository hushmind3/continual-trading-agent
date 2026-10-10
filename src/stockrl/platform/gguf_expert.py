"""Frozen local GGUF market-context Expert using llama.cpp's native quantized kernels."""
import json
import os
import re
import socket
import subprocess
import tempfile
import time
import threading
from pathlib import Path
import requests
import numpy as np
from torch import nn
from .expert_packages import package_path,digest
from .llama_engine import ensure_engine

SCHEMA=dict(type='object',properties={
    'direction':dict(type='number',minimum=-1,maximum=1),
    'confidence':dict(type='number',minimum=0,maximum=1),
    'risk':dict(type='number',minimum=0,maximum=1)},required=['direction','confidence','risk'],additionalProperties=False)


class GGUFExpert(nn.Module):
    def __init__(self,settings,package):
        super().__init__();self.settings=settings;self.entry=package['entry'];self.reference=package['weight_asset']
        self.path=package_path(settings.model_dir/'expert_registry.json',self.reference)
        if digest(self.path)!=self.reference['sha256']:raise ValueError('GGUF 고정 가중치 checksum이 다릅니다.')
        self.child=None;self.device=None;self.log=None;self.log_dir=None;self.details={}

    def start(self,device):
        if self.child and self.child.poll() is None and self.device==device:return
        self.close();engine=ensure_engine(self.settings)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        self.url=f'http://127.0.0.1:{port}';self.device=device
        self.log=tempfile.TemporaryFile(mode='w+b')
        self.log_dir=tempfile.TemporaryDirectory(prefix='stockrl-llama-');self.log_path=Path(self.log_dir.name)/'engine.log'
        args=[str(engine),'-m',str(self.path),'--host','127.0.0.1','--port',str(port),
            '--log-file',str(self.log_path),'--reasoning','off','--log-verbosity','4']
        # The pinned llama.cpp server auto-fits GPU layers and keeps overflow in host RAM.
        if device=='cpu':args.extend(['--n-gpu-layers','0'])
        self.child=subprocess.Popen(args,stdout=self.log,stderr=self.log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        while True:
            if getattr(self,'cancelled',lambda:False)():self.close();raise InterruptedError('MoE 정지 요청')
            if self.child.poll() is not None:
                self.log.seek(0);detail=self.log.read().decode('utf8',errors='replace')[-1500:];self.close();raise ValueError('GGUF 원본 실행 실패: '+detail)
            try:
                if requests.get(self.url+'/health').ok:break
            except requests.RequestException:pass
            time.sleep(.2)
        self.log.seek(0);text=self.log.read().decode('utf8',errors='replace')
        if self.log_path.exists():text+='\n'+self.log_path.read_text(encoding='utf8',errors='replace')
        text=re.sub(r'\x1b\[[0-9;]*m','',text)
        layers=re.findall(r'offloaded (\d+)\s*/\s*(\d+) layers',text)
        self.details=dict(engine='llama.cpp Vulkan/CPU',gpu_layers=int(layers[-1][0]) if layers else None,total_layers=int(layers[-1][1]) if layers else None)
        buffers=dict(re.findall(r'((?:Vulkan|CUDA)\d[^\n]*?buffer size\s*=\s*([\d.]+) MiB)',text))
        self.details['resident_bytes']=int(sum(float(v) for v in buffers.values())*2**20) if buffers else None
        self.details['peak_vram_bytes']=self.details['resident_bytes']

    def forward(self,root,data,device='cpu'):
        self.start(device);outputs=[]
        for symbol,series in zip(data['symbols'],data['series']):
            if getattr(self,'cancelled',lambda:False)():raise InterruptedError('MoE 정지 요청')
            values=np.asarray(series[-32:],float)
            if len(values)<32 or not np.isfinite(values).all():raise ValueError('GGUF 시장 입력은 실제 관측 32개가 필요합니다.')
            # Actual relative prices; model output is a declared opinion, never a fabricated quote.
            relative=(values/max(abs(values[-1]),1e-9)-1).round(6).tolist()
            response=self.query(dict(messages=[
                dict(role='system',content='You are a frozen market analyst. Use only the observed prices. Return JSON: direction (-1 bearish to 1 bullish), confidence (0 to 1), risk (0 to 1). No future observations are given.'),
                dict(role='user',content=json.dumps(dict(symbol=symbol,relative_prices=relative,sampling_seconds=data['sampling_seconds'])))],
                response_format={'type':'json_schema','json_schema':{'name':'market_opinion','schema':SCHEMA}},
                max_tokens=256))
            response.raise_for_status();choice=response.json()['choices'][0]
            content=choice['message'].get('content')
            if not content:raise ValueError('GGUF 구조화 출력이 비었습니다. 종료 사유: '+str(choice.get('finish_reason')))
            try:value=json.loads(content)
            except json.JSONDecodeError as exc:raise ValueError('GGUF 출력이 JSON 계약과 다릅니다: '+content[:200]) from exc
            row=[float(value[k]) for k in ('direction','confidence','risk')]
            if not np.isfinite(row).all() or not -1<=row[0]<=1 or not all(0<=v<=1 for v in row[1:]):raise ValueError('GGUF 의견 출력이 입력 계약을 벗어났습니다.')
            outputs.append(row)
        return dict(native_output=outputs,symbols=data['symbols'],as_of=data['as_of'],sampling_seconds=data['sampling_seconds'],
            horizon=1,layout='symbol,direction_confidence_risk',units='model_opinion',output_shape=[len(outputs),3],frozen=True,**self.details)

    def query(self,payload):
        """A stop during native generation cancels the child instead of waiting on HTTP."""
        done=threading.Event();result={}
        def receive():
            try:result['response']=requests.post(self.url+'/v1/chat/completions',json=payload)
            except Exception as exc:result['error']=exc
            finally:done.set()
        thread=threading.Thread(target=receive,name='gguf-response',daemon=True);thread.start()
        while not done.wait(.2):
            if getattr(self,'cancelled',lambda:False)():
                self.close();thread.join();raise InterruptedError('MoE 정지 요청')
        if 'error' in result:raise result['error']
        return result['response']

    def offload(self):self.close()

    def close(self):
        if self.child and self.child.poll() is None:
            self.child.terminate()
            self.child.wait()
        self.child=None
        if self.log:self.log.close();self.log=None
        if self.log_dir:self.log_dir.cleanup();self.log_dir=None
