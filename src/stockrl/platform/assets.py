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
from .expert_packages import HEADER_FORMAT,load_package,package_path


def guard_model_assets(path,extra_references=()):
    bank=Path(path).resolve();reads=set()
    saved=torch.load(bank,map_location='cpu',weights_only=True,mmap=True) if bank.is_file() else {}
    allowed={bank}
    if saved.get('format')==HEADER_FORMAT:
        allowed.update(package_path(bank,r) for r in saved['expert_packages'].values())
    allowed.update(package_path(bank,r) for r in extra_references)
    del saved
    def audit(event,args):
        if event!='open' or not args or not isinstance(args[0],str):return
        candidate=Path(args[0])
        weight=candidate.suffix in ('.pt','.pth','.ckpt','.safetensors') or candidate.name=='pytorch_model.bin'
        if not weight:return
        candidate=candidate.resolve()
        if candidate not in allowed:
            raise RuntimeError('MoE에 등록되지 않은 가중치를 읽으려 했습니다: '+str(candidate))
        reads.add(str(candidate))
    sys.addaudithook(audit)
    return reads


class ExpertPool:
    def __init__(self, settings, extra_packages=None):
        self.settings = settings
        path = settings.resolve(settings.expert_checkpoint)
        self.path=path
        self.saved = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
        if self.saved.get('format')==HEADER_FORMAT:
            self.saved=torch.load(path,map_location='cpu',weights_only=True)
        if self.saved.get("format") not in ("registered_vertical_trading_moe_v1",HEADER_FORMAT):
            raise ValueError("Expert 자산 패키지 형식을 확인하세요.")
        self.entries = self.saved["expert_mapping"]
        for key,reference in (extra_packages or {}).items():
            package=load_package(path,reference,verify=True)
            self.entries[key]=package['entry'];self.saved['expert_packages'][key]=reference
            self.saved['config']['feature_sizes'][key]=package['feature_size']
            self.saved['config']['native_module_counts'][key]=package['module_count']
        self.active=set(self.saved.get('active_experts',settings.enabled_experts or self.entries))
        missing=[]
        for key in self.entries:
            count=self.saved['config']['native_module_counts'].get(key,0)
            if not count:missing.append(key)
            for index in range(count):
                if self.saved['format']!=HEADER_FORMAT and not any(name.startswith(f'experts.{key}.models.{index}.') for name in self.saved['state_dict']):
                    missing.append(f'{key}/{index}')
        if missing:
            raise RuntimeError('champion.pt에 Expert 가중치가 누락됐습니다. 원본으로 다시 패키징해야 합니다: '+', '.join(missing))
        self.temp = tempfile.TemporaryDirectory(prefix="finrlx-expert-definitions-")
        self.root = Path(self.temp.name)
        with zipfile.ZipFile(io.BytesIO(self.saved["metadata"]["architecture_sources"])) as archive:
            for item in archive.infolist():
                if not (self.root/item.filename).resolve().is_relative_to(self.root.resolve()):
                    raise ValueError("잘못된 Expert 정의 경로")
                if item.file_size > 20*1024*1024:
                    raise ValueError("Expert 정의 파일이 지나치게 큽니다.")
            archive.extractall(self.root)
        self.loaded = OrderedDict()
        self.roots={key:self.root for key in self.entries}
        self.metrics = {}
        self.process = psutil.Process()
        self.ids = sorted(self.entries)

    def model_spec(self):
        config={k:self.saved["config"][k] for k in ("feature_sizes","stock_policy_ids","assembly_routing") if k in self.saved["config"]}
        return {"config":config,"expert_ids":self.ids,
                "source_updates":int(self.saved.get("optimizer_updates",0))}

    def catalog(self):
        return [dict(id=key, name=e.get("name", key), role="action" if e.get("stock_policy") else "market",
                     frozen=True, parameters=e.get("parameters"), symbols=e.get("stock_policy", {}).get("universe"),
                     enabled=key in self.active,
                     **{**self.metrics.get(key,{}),'loaded':key in self.loaded}) for key,e in sorted(self.entries.items())]

    def get(self, key):
        if key in self.loaded:
            self.loaded.move_to_end(key)
            return self.loaded[key]
        entry=self.entries[key]
        reserve=self.settings.resources.ram_reserve_gib*2**30
        estimated=max(float(entry.get('weight_bytes',0))*1.25,self.metrics.get(key,{}).get('peak_ram_increment',0))
        while self.loaded and (len(self.loaded) >= self.settings.resources.expert_cache_count or
                psutil.virtual_memory().available < reserve+estimated):
            self.loaded.popitem(last=False)
            gc.collect()
        if psutil.virtual_memory().available < reserve+estimated:
            raise MemoryError("사용 가능한 RAM이 운영 여유 공간보다 적습니다.")
        started = time.perf_counter()
        rss_before=self.process.memory_info().rss
        prefix = f"experts.{key}.models."
        count = self.saved["config"]["native_module_counts"][key]
        metadata=self.saved['metadata']
        if self.saved['format']==HEADER_FORMAT:
            package=load_package(self.path,self.saved['expert_packages'][key])
            if package['id']!=key or package['module_count']!=count:raise ValueError('Expert 패키지 구성이 다릅니다.')
            weights=package['state_dict'];prefix='models.';metadata=package['metadata']
            self.roots[key]=self.root/key
            with zipfile.ZipFile(io.BytesIO(metadata['architecture_sources'])) as archive:
                for item in archive.infolist():
                    if not (self.roots[key]/item.filename).resolve().is_relative_to(self.roots[key].resolve()):
                        raise ValueError('잘못된 Expert 정의 경로')
                    if item.file_size>20*1024*1024:raise ValueError('지나치게 큰 Expert 정의')
                archive.extractall(self.roots[key])
        else:weights=self.saved['state_dict']
        states = [{k.removeprefix(prefix+str(i)+"."):v for k,v in weights.items()
                   if k.startswith(prefix+str(i)+".")} for i in range(count)]
        if entry.get("stock_policy"):
            expert = StockPolicyExpert.restore(entry, states[0])
        else:
            def construct():
                data=metadata.get('construction_input') if self.saved['format']==HEADER_FORMAT else metadata['construction_inputs'][key]
                return native_call(entry['backend'],self.roots[key],data,
                                   states=states,load_only=True,runner_source=metadata['native_runner_source'])
            try:
                with torch.device('meta'):
                    modules=construct()
                if any(t.is_meta for m in modules for t in list(m.parameters())+list(m.buffers())):
                    raise NotImplementedError('Native architecture has nonpersistent meta buffers')
            except NotImplementedError:
                gc.collect();modules=construct()
            expert = NativeExpert(modules, entry,metadata['native_runner_source'])
        expert.requires_grad_(False).eval()
        self.loaded[key] = expert
        self.metrics.setdefault(key, {}).update(load_seconds=time.perf_counter()-started,loaded=True,
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
        device = "cpu"
        preference=self.settings.resources.expert_devices.get(key,'auto')
        large=int(self.entries[key].get('parameters',0))>=self.settings.resources.isolated_expert_parameters
        if preference!='cpu' and (large or preference=='cuda:0') and torch.cuda.is_available():
            free, total = torch.cuda.mem_get_info()
            weight_bytes=sum(p.numel()*p.element_size() for p in expert.parameters())
            required = max(prior_peak*1.1,weight_bytes*1.05) if prior_peak else weight_bytes*1.35
            if free - required > self.settings.resources.vram_reserve_gib * 2**30:
                device = "cuda:0"
                torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            floating=next((p.dtype for p in expert.parameters() if p.is_floating_point()),torch.float32)
            reduced=floating in (torch.float16,torch.bfloat16)
            with torch.autocast('cuda' if device.startswith('cuda') else 'cpu',dtype=floating if reduced else torch.bfloat16,enabled=reduced):
                packet = expert(self.roots[key], data, device)
        if any(p.requires_grad or p.grad is not None for p in expert.parameters()):
            raise RuntimeError("Expert가 고정 가중치 상태를 벗어났습니다.")
        packet["expert"] = key
        if data.get("observation_timestamps"):
            packet['symbol_as_of']={symbol:stamps[-1] for symbol,stamps in zip(data['symbols'],data['observation_timestamps'])}
        packet["native_features_verified"] = True
        metrics = self.metrics.setdefault(key, {})
        metrics.update(status="ready", device=device, inference_seconds=time.perf_counter()-started,
                       rss_bytes=self.process.memory_info().rss,
                       peak_ram_bytes=getattr(self.process.memory_info(), "peak_wset", self.process.memory_info().rss),
                       peak_vram_bytes=max(prior_peak,torch.cuda.max_memory_allocated() if device.startswith("cuda") else 0),
                       last_as_of=packet.get("as_of"), error=None)
        if device.startswith("cuda"):
            torch.cuda.empty_cache()
        return packet

    def close(self):
        self.loaded.clear()
        self.saved = None
        gc.collect()
        self.temp.cleanup()
