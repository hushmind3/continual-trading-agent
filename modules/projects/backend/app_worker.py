"""One reusable ASGI worker per active imported app; no listening HTTP port."""
import asyncio
import base64
import importlib
import json
import os
import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_hook import ProviderHook

protocol = sys.stdout
sys.stdout = sys.stderr


async def request(app, message):
    body = str(message.get('body') or '').encode()
    path = message.get('path') or '/openapi.json'
    if not path.startswith('/') or '?' in path: raise ValueError('Invalid application path')
    headers = [(str(key).lower().encode(), str(value).encode()) for key, value in message.get('headers', {}).items()
               if key.lower() not in ('host', 'content-length', 'connection')]
    if message.get('_host'): headers.append((b'host', str(message['_host']).encode()))
    scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'method': message.get('method', 'GET'),
        'scheme': 'http', 'path': path, 'raw_path': path.encode(), 'root_path': '',
        'query_string': str(message.get('query', '')).encode(), 'headers': headers,
        'client': tuple(message.get('_client', ['platform-internal', 0])),
        'server': tuple(message.get('_server', ['127.0.0.1', 8766]))}
    response = {'status': 500, 'headers': {}, 'body': ''}; parts = []; sent = False
    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {'type': 'http.request', 'body': body, 'more_body': False}
        await asyncio.sleep(3600)
        return {'type': 'http.disconnect'}
    async def send(event):
        if event['type'] == 'http.response.start':
            response.update(status=event['status'], headers={k.decode(): v.decode() for k, v in event.get('headers', [])
                if k.lower() not in (b'content-length', b'transfer-encoding', b'content-encoding')})
        elif event['type'] == 'http.response.body':
            parts.append(event.get('body', b''))
            if sum(map(len, parts)) > 8 * 1024 * 1024: raise ValueError('Application response exceeds 8 MiB')
    await asyncio.wait_for(app(scope, receive, send), timeout=60)
    response['body'] = base64.b64encode(b''.join(parts)).decode()
    if message.get('inspect'):
        response['features'] = {'cookie_sessions': any(item.cls.__name__ == 'SessionMiddleware' for item in getattr(app, 'user_middleware', []))}
    return response


async def main():
    folder, target = sys.argv[1:3]
    if len(sys.argv) > 3:
        import site
        packages = sys.argv[3]
        site.addsitedir(packages); sys.path.insert(0, packages)
    os.chdir(folder); sys.path.insert(0, folder)
    module, name = target.split(':')
    app = getattr(importlib.import_module(module), name)
    # Company integration is a records facade. It must not create another AI provider.
    integrated = len(sys.argv) > 6
    hook = ProviderHook(sys.argv[4], protocol) if not integrated and len(sys.argv) > 4 and sys.argv[4] else None
    application_active=0
    def activity(delta):
        nonlocal application_active
        application_active=max(0,application_active+delta)
        protocol.write(json.dumps({'application_activity':application_active})+'\n');protocol.flush()
    if integrated:
        from importlib import util
        spec=util.spec_from_file_location('application_workflow',sys.argv[5])
        integration=util.module_from_spec(spec);spec.loader.exec_module(integration)
        integration.install(app,sys.argv[6],activity)
    tasks = set()
    async def handle(message):
        try: result = await request(app, message)
        except Exception as exc:
            traceback.print_exc(file=sys.stderr); result = {'error': str(exc)}
        protocol.write(json.dumps(result) + '\n'); protocol.flush()
    async with app.router.lifespan_context(app):
        while line := await asyncio.to_thread(sys.stdin.readline):
            message = json.loads(line)
            if hook and message.get('harness_result'):
                hook.receive(message); continue
            task = asyncio.create_task(handle(message)); tasks.add(task); task.add_done_callback(tasks.discard)
        for task in tasks: task.cancel()
        if tasks: await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == '__main__':
    asyncio.run(main())
