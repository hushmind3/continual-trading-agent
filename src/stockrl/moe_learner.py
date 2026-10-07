"""Bounded asynchronous CPU learning; collector owns accounts and durable writes."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from types import SimpleNamespace
import time
import psutil
import torch
from .trading_moe import TradingMoE
from .moe_training import update_batch


class AsyncLearner:
    def __init__(self, model, optimizer, rules):
        # Copy only <1M trainable parameters, never the GB native Expert bodies.
        self.model = SimpleNamespace(controller=deepcopy(model.controller).cpu(),
            adapters=deepcopy(model.adapters).cpu(), config=deepcopy(model.config),
            optimizer_updates=model.optimizer_updates)
        self.model.prepare = lambda packets, symbols: TradingMoE.prepare(self.model, packets, symbols)
        self.model.policy_q = lambda packets, symbols: TradingMoE.policy_q(self.model, packets, symbols)
        if hasattr(model, 'assembly_enabled'):
            self.model.assembly_enabled = set(model.assembly_enabled)
        groups = [{'name': g['name'], 'params': list(module.parameters())} for g, module in
                  zip(optimizer.param_groups, (self.model.adapters, self.model.controller))]
        if len(optimizer.param_groups) != 2:
            raise ValueError('online learner accepts frozen Experts and trainable adapters/controller only')
        self.optimizer = torch.optim.AdamW(groups, lr=rules['learning_rate'])
        self.optimizer.load_state_dict(deepcopy(optimizer.state_dict()))
        for state in self.optimizer.state.values():
            for key, value in state.items():
                if isinstance(value, torch.Tensor):state[key] = value.cpu()
        self.rules = rules
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='moe-learner')
        self.future = None; self.records = []; self.error = None
        self.stats = dict(device='cpu', capacity=1, queue=0, updates=model.optimizer_updates,
                          contexts=0, queue_wait_seconds=0., training_seconds=0., deferred=0)
        self.ram_delta = 0

    @property
    def busy(self):
        return self.future is not None

    def submit(self, records):
        if self.busy or not records:return False
        required = int(self.rules['learner_ram_reserve_mib'])*1024**2 + self.ram_delta
        if psutil.virtual_memory().available < required:
            self.stats['deferred'] += 1
            return False
        self.records = records
        requested = time.perf_counter()
        self.stats['queue'] = 1
        self.future = self.executor.submit(self._learn, records, requested)
        return True

    def _learn(self, records, requested):
        started = time.perf_counter(); rss = psutil.Process().memory_info().rss
        latest = None
        for _ in range(int(self.rules['training_optimizer_steps'])):
            latest = update_batch(self.model, self.optimizer, records, settings=self.rules)
        self.ram_delta = max(self.ram_delta, psutil.Process().memory_info().rss-rss)
        return dict(latest, queue_wait_seconds=started-requested,
                    training_seconds=time.perf_counter()-started)

    def poll(self, model, optimizer, *, wait=False):
        if not self.future or (not wait and not self.future.done()):return None
        try:
            result = self.future.result()
        except Exception as exc:
            self.error = f'{type(exc).__name__}: {exc}'
            self.stats.update(queue=0, error=self.error)
            # Restore from the last published state if the optimizer failed.
            self.model.controller.load_state_dict(model.controller.state_dict())
            self.model.adapters.load_state_dict(model.adapters.state_dict())
            self.model.optimizer_updates = model.optimizer_updates
            self.optimizer.load_state_dict(deepcopy(optimizer.state_dict()))
            for state in self.optimizer.state.values():
                for key, value in state.items():
                    if isinstance(value, torch.Tensor):state[key] = value.cpu()
            self.future = None; self.records = []
            return None
        model.controller.load_state_dict(self.model.controller.state_dict())
        model.adapters.load_state_dict(self.model.adapters.state_dict())
        model.optimizer_updates = self.model.optimizer_updates
        optimizer.load_state_dict(deepcopy(self.optimizer.state_dict()))
        records = self.records
        self.future = None; self.records = []; self.error = None
        self.stats.update(result, queue=0, error=None, updates=model.optimizer_updates)
        return result, records

    def close(self):
        self.executor.shutdown(wait=True, cancel_futures=False)
