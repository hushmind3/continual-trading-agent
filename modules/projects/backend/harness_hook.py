"""Child-process async provider hook; source files and standalone behavior stay original."""
import asyncio
import functools
import importlib
import inspect
import json
import uuid


class ProviderHook:
    def __init__(self, entry, output):
        self.pending = {}; self.output = output
        module, name = entry.split(':')
        provider = importlib.import_module(module)
        original = getattr(provider, name)
        signature = inspect.signature(original)
        @functools.wraps(original)
        async def compose(*args, **kwargs):
            arguments = signature.bind(*args, **kwargs); arguments.apply_defaults()
            system,user=arguments.arguments['system'],arguments.arguments['user']
            return await self.request({'system':system,'user':user,'max_tokens':arguments.arguments.get('max_tokens')})
        setattr(provider, name, compose)
        if hasattr(provider, 'status'):
            async def status(): return await self.request({'operation': 'settings'})
            provider.status = status

    async def request(self, payload):
        key = uuid.uuid4().hex
        future = asyncio.get_running_loop().create_future(); self.pending[key] = future
        self.send({'harness_request': {'id': key, **payload}})
        try: return await asyncio.wait_for(future, 900)
        finally:
            self.pending.pop(key, None)
            if future.cancelled(): self.send({'harness_cancel': key})

    def send(self, value):
        self.output.write(json.dumps(value, ensure_ascii=False) + '\n'); self.output.flush()

    def receive(self, message):
        future = self.pending.get(message.get('id'))
        if future and not future.done():
            if message.get('error'): future.set_exception(RuntimeError(message['error']))
            else: future.set_result(message.get('text', ''))
