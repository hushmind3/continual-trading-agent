"""Preserve the official HTTP stream under the owning menu's single /api host."""
import asyncio
import base64
from ai_agent.Hermes.engine.bridge import bridge

PREFIX='/api/ai_agent/Hermes/native'


class OfficialASGI:
    async def __call__(self,scope,receive,send):
        path=scope['path']
        if path.startswith(PREFIX):path=path[len(PREFIX):] or '/'
        if scope['type']=='websocket':
            from urllib.parse import urlencode
            from fastapi import WebSocket
            from .websocket import serve_socket
            query=scope.get('query_string',b'').decode()
            value=path+('?' + query if query else '')
            forwarded={**scope,'query_string':urlencode({'operation':'ai_agent/Hermes/official/ws','path':value}).encode()}
            await serve_socket(WebSocket(forwarded,receive,send))
            return
        body=bytearray()
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            body.extend(message.get('body',b''))
            if not message.get('more_body'):break
        query=scope.get('query_string',b'').decode()
        payload={'path':path+('?' + query if query else ''),'method':scope['method'],
                 'scheme':scope.get('scheme','http'),'server':scope.get('server'),
                 'headers':{k.decode('latin1'):v.decode('latin1') for k,v in scope['headers']},
                 'body':base64.b64encode(body).decode()}
        opened=await asyncio.to_thread(bridge.call,'official/stream/open',payload)
        identifier=opened['id'];started=False
        async def disconnected():
            while True:
                if (await receive())['type']=='http.disconnect':return
        disconnect=asyncio.create_task(disconnected())
        try:
            while True:
                if disconnect.done():return
                value=await asyncio.to_thread(bridge.call,'official/stream/poll',{'id':identifier})
                for message in value['messages']:
                    kind=message['type']
                    if kind=='platform.complete':return
                    if kind=='platform.error':raise RuntimeError(message['detail'])
                    if kind=='http.response.start':
                        started=True
                        message['headers']=[(k.encode('latin1'),v.encode('latin1')) for k,v in message['headers']]
                    elif kind=='http.response.body':message['body']=base64.b64decode(message.get('body') or '')
                    await send(message)
                await asyncio.sleep(0.01)
        except Exception:
            if not started:
                await send({'type':'http.response.start','status':502,'headers':[(b'content-type',b'text/plain; charset=utf-8')]})
                await send({'type':'http.response.body','body':'공식 기능 연결에서 오류가 발생했습니다.'.encode()})
            else:raise
        finally:
            disconnect.cancel()
            await asyncio.gather(disconnect,return_exceptions=True)
            await asyncio.to_thread(bridge.call,'official/stream/close',{'id':identifier})


def register_host(app):
    app.mount(PREFIX,OfficialASGI(),name='hermes-official-api')
