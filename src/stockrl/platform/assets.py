"""Lazy, measured residency for the original frozen Expert assets only."""
from __future__ import annotations

from collections import OrderedDict
import gc
import io
import tempfile
import time
import zipfile
from pathlib import Path
import psutil
import torch
import sys

from ..moe_native import NativeExpert, native_call
from ..moe_stock_policies import StockPolicyExpert
from .expert_packages import load_package
from ..expert_device import restore_host



class ExpertPool:
    def __init__(self, settings,keep_device=False,live=False,extra_packages=None):
        self.settings = settings
        self.keep_device=keep_device
        self.live=live
        from ..state_io import read_json
        catalog=read_json(settings.registry_file)
        for key,reference in (extra_packages or {}).items():
            catalog.setdefault('experts',{})[key]={'package':reference}
        self.path=settings.model_dir/'expert_registry.json'
        self.entries={};references={};sizes={};counts={}
        for key,item in catalog.get('experts',{}).items():
            package=load_package(self.path,item['package'])
            self.entries[key]={**package['entry'],'id':key};references[key]=item['package']
            sizes[key]=package['feature_size'];counts[key]=package['module_count']
        self.references=references;self.counts=counts
        self.active=set(catalog.get('active',[]))
        self.temp=tempfile.TemporaryDirectory(prefix='frozen-expert-definitions-')
        self.root=Path(self.temp.name)
        self.loaded = OrderedDict()
        self.roots={key:self.root for key in self.entries}
        self.metrics = {}
        self.process = psutil.Process()
        self.ids = sorted(self.entries)
        from .expert_residency import Residency
        self.residency=Residency(self)

    def catalog(self):
        return [dict(id=key, name=e.get("name", key), role="action" if e.get("stock_policy") else "market",
                     frozen=True, parameters=e.get("parameters"), symbols=e.get("stock_policy", {}).get("universe"),
                     enabled=key in self.active,
                     **{**self.metrics.get(key,{}),'loaded':key in self.loaded}) for key,e in sorted(self.entries.items())]

    def get(self, key, *, structure_only=False):
        if key in self.loaded:
            self.loaded.move_to_end(key)
            return self.loaded[key]
        entry=self.entries[key]
        estimated=max(float(entry.get('weight_bytes',0)),self.metrics.get(key,{}).get('peak_ram_increment',0))
        while self.loaded and psutil.virtual_memory().available < estimated:
            self.release(next(iter(self.loaded)))
        if psutil.virtual_memory().available < estimated:
            raise MemoryError("사용 가능한 RAM이 Expert 적재에 부족합니다.")
        started = time.perf_counter()
        rss_before=self.process.memory_info().rss
        count = self.counts[key]
        package=load_package(self.path,self.references[key],verify=True)
        if package['module_count']!=count:raise ValueError('Expert 패키지 구성이 다릅니다.')
        if package.get('executor')=='llama_cpp':
            from .gguf_expert import GGUFExpert
            expert=GGUFExpert(self.settings,package);expert.keep_device=self.keep_device
            expert.cancelled=getattr(self,'cancelled',lambda:False)
            self.loaded[key]=expert
            self.metrics.setdefault(key,{}).update(load_seconds=time.perf_counter()-started,loaded=True,engine='llama.cpp',weight_bytes=package['weight_asset']['bytes'])
            return expert
        weights=package['state_dict'];prefix='models.';metadata=package['metadata']
        quantization=package.get('quantization')
        self.roots[key]=self.root/key
        with zipfile.ZipFile(io.BytesIO(metadata['architecture_sources'])) as archive:
            for item in archive.infolist():
                if not (self.roots[key]/item.filename).resolve().is_relative_to(self.roots[key].resolve()):
                    raise ValueError('잘못된 Expert 정의 경로')
                if item.file_size>20*1024*1024:raise ValueError('지나치게 큰 Expert 정의')
            archive.extractall(self.roots[key])
        states = [{k.removeprefix(prefix+str(i)+"."):v for k,v in weights.items()
                   if k.startswith(prefix+str(i)+".")} for i in range(count)]
        if package.get('executor')=='hf_forecast':
            from .hf_forecast import HfForecastExpert
            expert=HfForecastExpert.restore(package)
        elif entry.get("stock_policy"):
            expert = StockPolicyExpert.restore(entry, states[0],quantization)
        else:
            def construct():
                data=metadata.get('construction_input')
                return native_call(entry['backend'],self.roots[key],data,
                                   states=states,load_only=True,runner_source=metadata['native_runner_source'],quantization=quantization)
            try:
                with torch.device('meta'):
                    modules=construct()
                if not structure_only and any(t.is_meta for m in modules for t in list(m.parameters())+list(m.buffers())):
                    raise NotImplementedError('Native architecture has nonpersistent meta buffers')
            except NotImplementedError:
                gc.collect();modules=construct()
            expert = NativeExpert(modules, entry,metadata['native_runner_source'])
        expert.requires_grad_(False).eval()
        expert.keep_device=self.keep_device
        expert.retain_host_weights=not self.live
        self.loaded[key] = expert
        self.metrics.setdefault(key, {}).update(load_seconds=time.perf_counter()-started,loaded=True,
            load_count=self.metrics.get(key,{}).get('load_count',0)+1,
            peak_ram_increment=max(0,self.process.memory_info().rss-rss_before))
        return expert

    def run(self, key, data, snapshot):
        started = time.perf_counter()
        expert = self.get(key)
        if self.entries[key].get("stock_policy"):
            data = expert.prepare_input(snapshot)
            if data is None:
                raise ValueError("기존 학습 종목 전체의 실제 일봉·계좌 또는 필수 지표가 부족합니다.")
        if data is None:
            raise ValueError("현재 시세에서 이 Expert의 원본 입력을 만들 수 없습니다.")
        prior_peak = self.metrics.get(key, {}).get("peak_vram_bytes", 0)
        device=self.residency.device(key,expert,prior_peak)
        preference=self.settings.resources.expert_devices.get(key,'auto')
        if device.startswith('cuda'):torch.cuda.reset_peak_memory_stats()
        allocated_before=torch.cuda.memory_allocated() if device.startswith('cuda') else 0
        if device=='cpu':restore_host(expert)
        if preference=='cuda:0' and device=='cpu':raise MemoryError('CUDA 지정 실행에 필요한 VRAM 여유가 부족합니다.')
        with torch.inference_mode():
            floating=next((p.dtype for p in expert.parameters() if p.is_floating_point()),torch.float32)
            reduced=floating in (torch.float16,torch.bfloat16)
            with torch.autocast('cuda' if device.startswith('cuda') else 'cpu',dtype=floating if reduced else torch.bfloat16,enabled=reduced):
                packet = expert(self.roots[key], {**data,'_tensor_output':getattr(self,'tensor_output',False)}, device)
        if any(p.requires_grad or p.grad is not None for p in expert.parameters()):
            raise RuntimeError("Expert가 고정 가중치 상태를 벗어났습니다.")
        packet["expert"] = key
        if data.get("observation_timestamps"):
            packet['symbol_as_of']={symbol:stamps[-1] for symbol,stamps in zip(data['symbols'],data['observation_timestamps'])}
        packet["native_features_verified"] = True
        metrics = self.metrics.setdefault(key, {})
        metrics.update(status="ready", device=device, inference_seconds=time.perf_counter()-started,
                       last_completed_at=time.time(),
                       inference_count=metrics.get('inference_count',0)+1,
                       residency='gpu_ram_layer_offload' if getattr(expert,'_layer_offloaded',False) else 'gpu_resident' if self.keep_device and device.startswith('cuda') else 'ram_offload' if self.keep_device else 'temporary',
                       resident_bytes=sum(p.numel()*p.element_size() for p in list(expert.parameters())+list(expert.buffers()) if p.is_cuda),
                       rss_bytes=self.process.memory_info().rss,
                       peak_ram_bytes=getattr(self.process.memory_info(), "peak_wset", self.process.memory_info().rss),
                       peak_workspace_bytes=max(metrics.get('peak_workspace_bytes',0),max(0,torch.cuda.max_memory_allocated()-allocated_before)) if device.startswith('cuda') else metrics.get('peak_workspace_bytes',0),
                       peak_vram_bytes=max(0,torch.cuda.max_memory_allocated()-allocated_before)+sum(p.numel()*p.element_size() for p in list(expert.parameters())+list(expert.buffers()) if p.is_cuda) if device.startswith('cuda') else 0,
                       memory_measurement='model residency + inference allocation delta',
                       last_as_of=packet.get("as_of"), error=None)
        source_time=max(packet.get('symbol_as_of',{}).values(),default=packet.get('as_of') or '')
        if source_time>(metrics.get('latest_input_as_of') or ''):
            metrics.update(latest_input_as_of=source_time,new_input_count=metrics.get('new_input_count',0)+1,last_new_input_at=time.time())
        if hasattr(expert,'details'):
            import psutil
            child=psutil.Process(expert.child.pid).memory_info() if expert.child else None
            metrics.update(**expert.details,device='gpu' if expert.details.get('gpu_layers') else 'cpu',
                residency='gpu_resident' if expert.details.get('gpu_layers')==expert.details.get('total_layers') else 'gpu_cpu_hybrid' if expert.details.get('gpu_layers') else 'ram_offload',
                peak_ram_bytes=self.process.memory_info().rss+(getattr(child,'peak_wset',child.rss) if child else 0))
        if device.startswith("cuda") and not self.keep_device:
            torch.cuda.empty_cache()
        return packet

    def release(self,key):
        self.residency.pinned.discard(key)
        expert=self.loaded.pop(key)
        if not getattr(expert,'_gpu_owned',False):restore_host(expert)
        if hasattr(expert,'close'):expert.close()
        self.metrics.setdefault(key,{}).update(loaded=False,residency='unloaded',resident_bytes=0)
        gc.collect()
        if torch.cuda.is_available():torch.cuda.empty_cache()

    def close(self):
        for key in list(self.loaded):self.release(key)
        self.references={}
        gc.collect()
        self.temp.cleanup()
