"""Run the complete official ASGI application in the existing Hermes worker.

No second public server, reduced endpoint list, mock response or second home.
The platform transport carries HTTP/WebSocket messages to the real application.
"""
from __future__ import annotations

import asyncio
import base64
import json
import queue
import threading
import uuid
from urllib.parse import urlsplit, parse_qsl, urlencode


class OfficialApplication:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, name='hermes-official-api', daemon=True)
        self.thread.start()
        self.ready = None
        self.sockets = {}
        self.streams = {}
        self.lock = threading.Lock()
        self.closed = False

    async def _initialize(self):
        import httpx
        from hermes_cli.web_server import app, _SESSION_TOKEN
        self.app, self.token = app, _SESSION_TOKEN
        self.lifespan = app.router.lifespan_context(app)
        await self.lifespan.__aenter__()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://127.0.0.1:8766', timeout=None)
        # The main platform uses the real gateway for persistent sessions,
        # scheduled jobs and kanban dispatch, including after a host reboot.
        state = await self.client.get('/api/status',headers=self._headers())
        state.raise_for_status()
        if not state.json().get('gateway_running'):
            started = await self.client.post('/api/gateway/start',headers=self._headers(),json={})
            started.raise_for_status()

    def _submit(self, coroutine, timeout=120):
        with self.lock:
            if self.ready is None:
                self.ready = asyncio.run_coroutine_threadsafe(self._initialize(), self.loop)
        self.ready.result(timeout)
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop).result(timeout)

    def _headers(self, headers=None):
        supplied = {str(k).lower(): str(v) for k, v in (headers or {}).items()
                    if str(k).lower() not in {'host', 'content-length', 'cookie', 'authorization', 'origin'}}
        supplied.update({'x-hermes-session-token': self.token, 'origin': 'http://127.0.0.1:8766', 'host': '127.0.0.1:8766'})
        return supplied

    @staticmethod
    def _path(path):
        parsed = urlsplit(str(path))
        if parsed.scheme or parsed.netloc or not parsed.path.startswith('/') or parsed.path.startswith('//'):
            raise ValueError('공식 Hermes의 등록된 기능 경로만 호출할 수 있습니다.')
        return parsed

    async def _http(self, payload):
        parsed = self._path(payload.get('path', ''))
        response = await self.client.request(str(payload.get('method', 'GET')).upper(), parsed.geturl(),
            headers=self._headers(payload.get('headers')),
            content=base64.b64decode(payload.get('body') or '', validate=True))
        return {'status': response.status_code, 'headers': dict(response.headers),
                'body': base64.b64encode(response.content).decode('ascii')}

    async def _stream(self, payload, identifier, outgoing):
        parsed = self._path(payload.get('path', ''))
        disconnect = asyncio.Event()
        self.streams[identifier]['disconnect'] = disconnect
        received = False
        async def receive():
            nonlocal received
            if not received:
                received = True
                return {'type':'http.request','body':base64.b64decode(payload.get('body') or '',validate=True),'more_body':False}
            await disconnect.wait()
            return {'type':'http.disconnect'}
        async def send(message):
            value = dict(message)
            if 'headers' in value:value['headers']=[(k.decode('latin1'),v.decode('latin1')) for k,v in value['headers']]
            if isinstance(value.get('body'),bytes):value['body']=base64.b64encode(value['body']).decode('ascii')
            await asyncio.to_thread(outgoing.put,value)
        headers = self._headers(payload.get('headers'))
        public_host = (payload.get('headers') or {}).get('host','127.0.0.1:8766')
        headers['host'] = public_host
        headers['origin'] = str(payload.get('scheme','http'))+'://'+public_host
        headers['x-forwarded-prefix'] = '/api/ai_agent/Hermes/native'
        scope = {'type':'http','asgi':{'version':'3.0','spec_version':'2.4'},'http_version':'1.1',
                 'method':str(payload.get('method','GET')).upper(),'scheme':payload.get('scheme','http'),'root_path':'',
                 'path':parsed.path,'raw_path':parsed.path.encode(),'query_string':parsed.query.encode(),
                 'headers':[(k.encode('latin1'),v.encode('latin1')) for k,v in headers.items()],
                 'client':('127.0.0.1',0),'server':('127.0.0.1',8766),'state':{}}
        try:await self.app(scope,receive,send)
        except Exception as exc:
            await asyncio.to_thread(outgoing.put,{'type':'platform.error','detail':str(exc)})
        finally:await asyncio.to_thread(outgoing.put,{'type':'platform.complete'})

    async def _open_stream(self,payload):
        identifier=uuid.uuid4().hex
        outgoing=queue.Queue(maxsize=32)
        self.streams[identifier]={'outgoing':outgoing,'mutating':str(payload.get('method','GET')).upper() not in ('GET','HEAD','OPTIONS')}
        self.streams[identifier]['task']=asyncio.create_task(self._stream(payload,identifier,outgoing))
        await asyncio.sleep(0)
        return {'id':identifier}

    async def _close_stream(self,payload):
        state=self.streams.pop(str(payload['id']),None)
        if state:
            while not state['outgoing'].empty():
                try:state['outgoing'].get_nowait()
                except queue.Empty:break
            state['disconnect'].set()
            state['task'].cancel()
            await asyncio.gather(state['task'],return_exceptions=True)
        return {'closed':True}

    async def _socket(self, payload, identifier, outgoing):
        parsed = self._path(payload.get('path', ''))
        incoming = asyncio.Queue()
        self.sockets[identifier]['incoming'] = incoming
        await incoming.put({'type': 'websocket.connect'})
        query = dict(parse_qsl(parsed.query)); query['token'] = self.token
        scope = {'type': 'websocket', 'asgi': {'version': '3.0', 'spec_version': '2.4'},
                 'scheme': 'ws', 'path': parsed.path, 'raw_path': parsed.path.encode(),
                 'query_string': urlencode(query).encode(), 'headers': [(k.encode(), v.encode()) for k,v in self._headers().items()],
                 'client': ('127.0.0.1', 0), 'server': ('127.0.0.1', 8766), 'subprotocols': payload.get('subprotocols',[]), 'root_path': '', 'state': {}}
        closed = False
        async def send(message):
            nonlocal closed
            if message['type'] == 'websocket.close': closed = True
            value = dict(message)
            if isinstance(value.get('bytes'), bytes):
                value['bytes'] = base64.b64encode(value['bytes']).decode('ascii')
            outgoing.put(value)
        try:
            await self.app(scope, incoming.get, send)
        except Exception as exc:
            closed = True
            outgoing.put({'type': 'websocket.close', 'code': 1011, 'reason': str(exc)})
        finally:
            if not closed: outgoing.put({'type':'websocket.close','code':1000})

    async def _open_socket(self, payload):
        identifier = uuid.uuid4().hex
        outgoing = queue.Queue()
        self.sockets[identifier] = {'outgoing': outgoing}
        self.sockets[identifier]['task'] = asyncio.create_task(self._socket(payload, identifier, outgoing))
        await asyncio.sleep(0)
        return {'id': identifier}

    async def _send_socket(self, payload):
        state = self.sockets[str(payload['id'])]
        message = {'type': 'websocket.receive'}
        if 'bytes' in payload:
            message['bytes'] = base64.b64decode(payload['bytes'], validate=True)
        else:
            message['text'] = str(payload.get('text', ''))
        await state['incoming'].put(message)
        return {'sent': True}

    async def _close_socket(self, payload):
        state = self.sockets.pop(str(payload['id']), None)
        if state:
            await state['incoming'].put({'type': 'websocket.disconnect', 'code': 1000})
            try:
                await asyncio.wait_for(asyncio.shield(state['task']), timeout=5)
            except asyncio.TimeoutError:
                state['task'].cancel()
        return {'closed': True}

    def execute(self, operation, payload):
        if operation == 'official/stream/open':return self._submit(self._open_stream(payload))
        if operation == 'official/stream/close':return self._submit(self._close_stream(payload))
        if operation == 'official/stream/poll':
            state=self.streams.get(str(payload['id']))
            if not state:return {'messages':[{'type':'platform.complete'}]}
            messages=[]
            while len(messages)<32:
                try:messages.append(state['outgoing'].get_nowait())
                except queue.Empty:break
            return {'messages':messages}
        if operation == 'official/catalog':
            async def catalog():
                return {'paths': {path: sorted(method.upper() for method in methods if method in {'get','post','put','patch','delete','head','options'})
                                  for path,methods in self.app.openapi()['paths'].items()},
                        'home': __import__('os').environ['HERMES_HOME']}
            return self._submit(catalog())
        if operation == 'official/http': return self._submit(self._http(payload))
        if operation == 'official/ws/open': return self._submit(self._open_socket(payload))
        if operation == 'official/ws/send': return self._submit(self._send_socket(payload))
        if operation == 'official/ws/close': return self._submit(self._close_socket(payload))
        if operation == 'official/ws/poll':
            state = self.sockets.get(str(payload['id']))
            if not state: return {'messages': [{'type': 'websocket.close', 'code': 1000}]}
            messages = []
            while len(messages) < 100:
                try: messages.append(state['outgoing'].get_nowait())
                except queue.Empty: break
            return {'messages': messages}
        raise ValueError('등록되지 않은 공식 기능 요청입니다.')

    def request(self, path, method='GET', value=None):
        payload = {'path': path, 'method': method}
        if value is not None:
            payload.update(headers={'content-type':'application/json'}, body=base64.b64encode(json.dumps(value).encode()).decode())
        response = self.execute('official/http', payload)
        content = base64.b64decode(response['body'])
        result = json.loads(content) if content else {}
        if response['status'] >= 400:
            raise RuntimeError(str(result.get('detail') or result.get('error') or '공식 기능 요청 실패'))
        return result

    def close(self):
        with self.lock:
            if self.closed:return
            self.closed=True
        async def stop():
            for identifier in list(self.streams): await self._close_stream({'id':identifier})
            for identifier in list(self.sockets): await self._close_socket({'id': identifier})
            if hasattr(self, 'client'): await self.client.aclose()
            if hasattr(self, 'lifespan'): await self.lifespan.__aexit__(None, None, None)
        try:
            asyncio.run_coroutine_threadsafe(stop(), self.loop).result(15)
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(5)

    def busy_reason(self):
        if self.ready is None:return ''
        async def proof():
            from hermes_cli.web_server_idle_proof import idle_proof
            return await asyncio.to_thread(idle_proof)
        result=self._submit(proof(),timeout=5)
        if result.get('idle') is not True:
            return '공식 헤르메스 작업·예약 실행·사용자 응답 대기 또는 상태 확인 불가: '+str(result.get('reason'))
        if any(value.get('mutating') for value in self.streams.values()):
            return '공식 헤르메스 설정·설치 작업 진행 중'
        return ''
