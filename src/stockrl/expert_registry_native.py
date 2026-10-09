"""Frozen Expert registration and inference; no trainable central model."""
from pathlib import Path
from types import SimpleNamespace
import json
import time
import numpy as np
import pandas as pd
from .framework import ROOT
from .state_io import read_json,atomic_json
from .platform.expert_packages import PACKAGE_FORMAT,digest,load_package
from .platform.expert_contracts import input_contract,descriptor


class ExpertRegistry:
    def __init__(self):
        self.registry_file=ROOT/'configs/experts.json'
        self.model_dir=Path.home()/'Desktop'/'모델'
        self.state_dir=ROOT/'runtime/experts';self.state_dir.mkdir(parents=True,exist_ok=True)
        resources=SimpleNamespace(expert_cache_count=128,ram_reserve_gib=4,vram_reserve_gib=1.5,
            expert_devices={},gguf_prompt_cache_mib=0,inference_timeout_seconds=180)
        self.settings=SimpleNamespace(registry_file=self.registry_file,model_dir=self.model_dir,
            state_dir=self.state_dir,resources=resources)
        self.pool=None;self.cache={};self.last_outputs={};self.signature=None;self.reported_at=0

    def catalog(self):return read_json(self.registry_file)

    def select(self,active):
        catalog=self.catalog()
        if not set(active)<=set(catalog['experts']):raise ValueError('등록되지 않은 Expert입니다.')
        catalog['active']=list(active);atomic_json(catalog,self.registry_file)
        self.close()

    def register(self,path,slot):
        import re,shutil,torch
        if not re.fullmatch('[a-z][a-z0-9_]{0,79}',slot):raise ValueError('슬롯 이름을 확인하세요.')
        source=Path(path).expanduser().resolve()
        package=json.loads(source.read_text(encoding='utf8')) if source.suffix=='.json' else torch.load(source,map_location='cpu',weights_only=True,mmap=True)
        if package.get('format')!=PACKAGE_FORMAT:raise ValueError('원본 구조·가중치·입력 계약을 포함한 Expert 패키지가 필요합니다.')
        contract=input_contract(package['entry'])
        if not contract['supported']:raise ValueError(contract['reason'])
        if package.get('weight_asset'):
            load_package(self.model_dir/'expert_registry.json',{'file':source.relative_to(self.model_dir).as_posix(),'sha256':digest(source),'bytes':source.stat().st_size},verify=True)
        checksum=digest(source);target=self.model_dir/'expert-packages'/(slot+'-'+checksum[:16]+source.suffix)
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.resolve()!=source:shutil.copyfile(source,target)
        ref={'file':target.relative_to(self.model_dir).as_posix(),'sha256':checksum,'bytes':target.stat().st_size}
        catalog=self.catalog();catalog.setdefault('experts',{})[slot]=descriptor(slot,package,ref)
        atomic_json(catalog,self.registry_file)
        self.close()

    def outputs(self,frame,account):
        from .platform.assets import ExpertPool
        from .platform.observations import native_input
        catalog=self.catalog();signature=json.dumps(catalog,sort_keys=True)
        if signature!=self.signature:
            self.close();self.last_outputs={};self.signature=signature
        if self.pool is None:self.pool=ExpertPool(self.settings,keep_device=True,live=True)
        stamp=str(frame.date.max());daily=frame[frame.date<pd.Timestamp(stamp).normalize()]
        groups={'market':[],'action':[]}
        for key in catalog.get('active',[]):
            entry=self.pool.entries[key];policy=entry.get('stock_policy');cache_key=(key,stamp)
            try:
                if not policy and cache_key in self.cache:packet=self.cache[cache_key]
                else:
                    snapshot={'symbols':sorted(frame.symbol.unique()),'as_of':stamp,'policy_account':account,
                        'stock_policy_history':daily.assign(date=daily.date.astype(str)).to_dict('records')}
                    if policy and account.get('currency','USD')!='USD':raise ValueError('이 Expert의 원본 계약은 USD 계좌입니다.')
                    batches=[None] if policy else native_input(entry['backend'],frame,daily,stamp)
                    packet=[self.pool.run(key,data,snapshot) for data in batches]
                    if not policy:self.cache[cache_key]=packet
                signals=[]
                for batch in packet:
                    values=np.asarray(batch['native_output'],dtype=float)
                    if policy:signals.extend((values[...,0]-values[...,2]).reshape(-1))
                    elif batch.get('units')=='price':
                        if batch.get('layout')=='nine_quantiles,batch,variate,horizon':values=values[:,0].transpose(1,0,2)
                        marks=frame.sort_values('date').groupby('symbol').close.last()
                        signals.extend(np.asarray(row).mean()/marks[symbol]-1 for symbol,row in zip(batch['symbols'],values))
                    else:signals.extend(values.reshape(-1))
                signal=np.asarray(signals,dtype=float)
                signal=signal[np.isfinite(signal)]
                if len(signal):groups['action' if policy else 'market'].append(float(signal.mean()))
                self.last_outputs[key]={'status':'ready','as_of':stamp,'output':signal.tolist()}
            except (ValueError,RuntimeError,MemoryError,OSError) as exc:
                self.last_outputs[key]={'status':'needs_input','reason':str(exc)}
        if time.monotonic()-self.reported_at>=5:
            atomic_json({'as_of':stamp,'experts':self.last_outputs,'resources':self.pool.metrics},self.state_dir/'status.json');self.reported_at=time.monotonic()
        if len(self.cache)>5000:self.cache.clear()
        result=[]
        for values in groups.values():
            result.extend([float(np.mean(values)),float(np.std(values)),float(np.max(np.abs(values))),float(len(values))] if values else [0.,0.,0.,0.])
        return np.array(result,dtype=np.float32)

    def close(self):
        if self.pool:self.pool.close()
        self.pool=None;self.cache.clear()
