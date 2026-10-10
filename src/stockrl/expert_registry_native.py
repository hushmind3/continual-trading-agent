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
    def __init__(self,pool_provider=None,champion=None):
        self.pool_provider=pool_provider
        self._embedded_temp=None;self.champion_catalog=None
        if champion is None:
            self.registry_file=ROOT/'configs/experts.json';self.model_dir=Path.home()/'Desktop'/'모델'
            self.state_dir=ROOT/'runtime/experts';self.state_dir.mkdir(parents=True,exist_ok=True)
        else:
            import tempfile,torch
            from .platform.expert_packages import digest
            self._embedded_temp=tempfile.TemporaryDirectory(prefix='sac-champion-experts-')
            root=Path(self._embedded_temp.name);self.model_dir=root/'models';self.model_dir.mkdir()
            self.registry_file=root/'configs'/'experts.json';self.registry_file.parent.mkdir()
            (self.model_dir/'expert_registry.json').write_text('{}',encoding='utf8')
            experts={};active=list(champion.get('identity',{}).get('champion_experts',[]))
            for key in active:
                package=dict(champion['expert_packages'][key]);weight_data=package.pop('weight_asset_data',None)
                if weight_data is not None:
                    asset_name=f'assets/{key}.gguf';asset_path=self.model_dir/asset_name
                    asset_path.parent.mkdir(parents=True,exist_ok=True);asset_path.write_bytes(weight_data)
                    package['weight_asset']={'file':asset_name,'sha256':digest(asset_path),'bytes':asset_path.stat().st_size}
                package_path=self.model_dir/f'{key}.pt';torch.save(package,package_path)
                experts[key]={'id':key,'name':package.get('entry',{}).get('name',key),
                    'package':{'file':package_path.name,'sha256':digest(package_path),'bytes':package_path.stat().st_size}}
            self.champion_catalog={'active':active,'experts':experts}
            self.registry_file.write_text(json.dumps(self.champion_catalog,ensure_ascii=False),encoding='utf8')
            self.state_dir=ROOT/'runtime/experts'/'champions'/str(champion.get('version',0))
            self.state_dir.mkdir(parents=True,exist_ok=True)
        resources=SimpleNamespace(expert_devices=read_json(ROOT/'configs/local/operations.json').get('expert_devices',{}))
        self.settings=SimpleNamespace(registry_file=self.registry_file,model_dir=self.model_dir,
            state_dir=self.state_dir,resources=resources)
        self.pool=None;self.cache={};self.last_outputs={};self.signature=None;self.reported_at=0

    def catalog(self):return self.champion_catalog or read_json(self.registry_file)

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
        checksum=digest(source)
        target=source if source.is_relative_to(self.model_dir.resolve()) else self.model_dir/'expert-packages'/(slot+'-'+checksum[:16]+source.suffix)
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.resolve()!=source:shutil.copyfile(source,target)
        ref={'file':target.relative_to(self.model_dir).as_posix(),'sha256':checksum,'bytes':target.stat().st_size}
        catalog=self.catalog();catalog.setdefault('experts',{})[slot]=descriptor(slot,package,ref)
        atomic_json(catalog,self.registry_file)
        self.close()

    def outputs(self,frame,account,champion_ids=None):
        from .platform.assets import ExpertPool
        from .platform.expert_inference import prepare_inputs,run_batches
        catalog=self.catalog();signature=json.dumps(catalog,sort_keys=True)
        if signature!=self.signature:
            self.close();self.last_outputs={};self.signature=signature
        if self.pool is None:self.pool=self.pool_provider() if self.pool_provider else ExpertPool(self.settings,keep_device=True,live=True)
        stamp=str(frame.date.max())
        groups={'market':[],'action':[]};champion_features={}
        selected=list(catalog.get('active',[])) if champion_ids is None else list(champion_ids)
        for key in selected:
            entry=self.pool.entries[key];policy=entry.get('stock_policy');cache_key=(key,stamp)
            try:
                if not policy and cache_key in self.cache:packet=self.cache[cache_key]
                else:
                    snapshot,batches=prepare_inputs(entry,frame,account)
                    packet=run_batches(self.pool,key,snapshot,batches)
                    if not policy:self.cache[cache_key]=packet
                signals=[];native_features=[]
                for batch in packet:
                    values=np.asarray(batch['native_output'],dtype=float)
                    native_features.extend(values.reshape(-1).tolist())
                    if policy:signals.extend((values[...,0]-values[...,2]).reshape(-1))
                    elif batch.get('units')=='price':
                        if batch.get('layout')=='nine_quantiles,batch,variate,horizon':values=values[:,0].transpose(1,0,2)
                        marks=frame.sort_values('date').groupby('symbol').close.last()
                        signals.extend(np.asarray(row).mean()/marks[symbol]-1 for symbol,row in zip(batch['symbols'],values))
                    else:signals.extend(values.reshape(-1))
                signal=np.asarray(signals,dtype=float)
                signal=signal[np.isfinite(signal)]
                if len(signal):groups['action' if policy else 'market'].append(float(signal.mean()))
                native=np.asarray(native_features,dtype=np.float64)
                native=native[np.isfinite(native)]
                if len(native):
                    native=np.sign(native)*np.log1p(np.minimum(np.abs(native),1e12))
                    chunks=np.array_split(native,64)
                    champion_features[key]=np.asarray([float(chunk.mean()) if len(chunk) else 0. for chunk in chunks],dtype=np.float32)
                else:champion_features[key]=np.zeros(64,dtype=np.float32)
                self.last_outputs[key]={'status':'ready','as_of':stamp,'output':signal.tolist()}
            except (ValueError,RuntimeError,MemoryError,OSError) as exc:
                self.last_outputs[key]={'status':'needs_input','reason':str(exc)}
        if time.monotonic()-self.reported_at>=5:
            atomic_json({'as_of':stamp,'experts':self.last_outputs,'resources':self.pool.metrics},self.state_dir/'status.json');self.reported_at=time.monotonic()
        if champion_ids is not None:
            return np.concatenate([champion_features.get(key,np.zeros(64,dtype=np.float32)) for key in champion_ids]) if champion_ids else np.empty(0,dtype=np.float32)
        result=[]
        for values in groups.values():
            result.extend([float(np.mean(values)),float(np.std(values)),float(np.max(np.abs(values))),float(len(values))] if values else [0.,0.,0.,0.])
        return np.array(result,dtype=np.float32)

    def close(self,cleanup=False):
        if self.pool and not self.pool_provider:self.pool.close()
        self.pool=None;self.cache.clear()
        if cleanup and self._embedded_temp:
            self._embedded_temp.cleanup();self._embedded_temp=None
