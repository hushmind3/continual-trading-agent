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

from ..moe_native import NativeExpert, native_call
from ..moe_stock_policies import StockPolicyExpert


class ExpertPool:
    def __init__(self, settings):
        self.settings = settings
        path = settings.resolve(settings.expert_checkpoint)
        self.saved = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
        if self.saved.get("format") != "registered_vertical_trading_moe_v1":
            raise ValueError("Expert 자산 패키지 형식을 확인하세요.")
        self.entries = self.saved["expert_mapping"]
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
        self.metrics = {}
        self.process = psutil.Process()
        self.ids = sorted(self.entries)

    def model_spec(self):
        config={k:self.saved["config"][k] for k in ("feature_sizes","stock_policy_ids","assembly_routing") if k in self.saved["config"]}
        return {"config":config,"expert_ids":self.ids,
                "source_updates":int(self.saved.get("optimizer_updates",0))}

    def catalog(self):
        return [dict(id=key, name=e.get("name", key), role="action" if e.get("stock_policy") or key.startswith("macrophft") else "market",
                     frozen=True, parameters=e.get("parameters"), symbols=e.get("stock_policy", {}).get("universe"),
                     enabled=not self.settings.enabled_experts or key in self.settings.enabled_experts,
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
        states = [{k.removeprefix(prefix+str(i)+"."):v for k,v in self.saved["state_dict"].items()
                   if k.startswith(prefix+str(i)+".")} for i in range(count)]
        if entry.get("stock_policy"):
            expert = StockPolicyExpert.restore(entry, states[0])
        else:
            def construct():
                return native_call(entry['backend'],self.root,self.saved['metadata']['construction_inputs'][key],
                                   states=states,load_only=True,runner_source=self.saved['metadata']['native_runner_source'])
            try:
                with torch.device('meta'):
                    modules=construct()
                if any(t.is_meta for m in modules for t in list(m.parameters())+list(m.buffers())):
                    raise NotImplementedError('Native architecture has nonpersistent meta buffers')
            except NotImplementedError:
                gc.collect();modules=construct()
            expert = NativeExpert(modules, entry)
        expert.requires_grad_(False).eval()
        self.loaded[key] = expert
        self.metrics.setdefault(key, {}).update(load_seconds=time.perf_counter()-started,loaded=True,
            peak_ram_increment=max(0,self.process.memory_info().rss-rss_before))
        return expert

    def run(self, key, data, snapshot):
        started = time.perf_counter()
        if self.entries[key].get('stock_policy',{}).get('kind')=='dapo' and not all(k in (snapshot.get('stock_policy_history') or [{}])[0] for k in ('llm_sentiment','llm_risk')):
            raise ValueError('원본 DAPO 정책에는 실제 LLM sentiment/risk 입력이 필요합니다.')
        expert = self.get(key)
        if self.entries[key].get("stock_policy"):
            data = expert.prepare_input(snapshot)
            if data is None:
                raise ValueError("기존 학습 종목 전체의 실제 일봉·계좌 또는 필수 지표가 부족합니다.")
        if data is None:
            raise ValueError("현재 시세에서 이 Expert의 원본 입력을 만들 수 없습니다.")
        prior_peak = self.metrics.get(key, {}).get("peak_vram_bytes", 0)
        device = "cpu"
        if torch.cuda.is_available():
            free, total = torch.cuda.mem_get_info()
            required = max(prior_peak, sum(p.numel()*p.element_size() for p in expert.parameters())*1.35)
            if free - required > self.settings.resources.vram_reserve_gib * 2**30:
                device = "cuda:0"
                torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            packet = expert(self.root, data, device)
        if any(p.requires_grad or p.grad is not None for p in expert.parameters()):
            raise RuntimeError("Expert가 고정 가중치 상태를 벗어났습니다.")
        packet["expert"] = key
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
