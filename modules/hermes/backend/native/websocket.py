"""Register the official real-time transport on the same platform /api host."""
import asyncio
from urllib.parse import urlparse
from fastapi import WebSocket, WebSocketDisconnect
from ai_agent.Hermes.engine.bridge import bridge


async def serve_socket(websocket: WebSocket):
    if websocket.query_params.get('operation') != 'ai_agent/Hermes/official/ws':
        await websocket.close(code=1008, reason='등록되지 않은 실시간 기능입니다.')
        return
    origin = websocket.headers.get('origin')
    if origin and urlparse(origin).netloc != websocket.headers.get('host'):
        await websocket.close(code=1008, reason='같은 플랫폼 화면에서 연결하세요.')
        return
    identifier = None
    try:
        opened = await asyncio.to_thread(bridge.call, 'official/ws/open', {'path': websocket.query_params.get('path',''), 'subprotocols':websocket.scope.get('subprotocols',[])})
        identifier = opened['id']
        accepted = False
        initial = []
        async with asyncio.timeout(30):
            while not accepted:
                first = await asyncio.to_thread(bridge.call, 'official/ws/poll', {'id': identifier})
                for message in first['messages']:
                    if message['type'] == 'websocket.accept':
                        accepted = True
                        subprotocol = message.get('subprotocol')
                    elif message['type'] == 'websocket.close':
                        await websocket.close(code=1008,reason='공식 기능이 연결을 거절했습니다.')
                        return
                    else: initial.append(message)
                if not accepted: await asyncio.sleep(0.03)
        await websocket.accept(subprotocol=subprotocol)
        async def receive():
            while True:
                value = await websocket.receive()
                if value['type'] == 'websocket.disconnect':return
                payload = {'id': identifier}
                if value.get('bytes') is not None:
                    import base64
                    payload['bytes'] = base64.b64encode(value['bytes']).decode()
                else:payload['text'] = value.get('text','')
                await asyncio.to_thread(bridge.call, 'official/ws/send', payload)
        async def send():
            pending = initial
            while True:
                value = await asyncio.to_thread(bridge.call, 'official/ws/poll', {'id': identifier})
                for message in pending + value['messages']:
                    if message['type'] == 'websocket.send':
                        if 'bytes' in message:
                            import base64
                            await websocket.send_bytes(base64.b64decode(message['bytes']))
                        else:await websocket.send_text(message.get('text',''))
                    elif message['type'] == 'websocket.close':
                        await websocket.close(code=message.get('code',1000),reason=message.get('reason','')[:100])
                        return
                pending = []
                await asyncio.sleep(0.05)
        tasks=[asyncio.create_task(receive()),asyncio.create_task(send())]
        try:await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in tasks:task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
    except WebSocketDisconnect:pass
    except Exception:
        try:await websocket.close(code=1011,reason='공식 실시간 연결에서 오류가 발생했습니다.')
        except RuntimeError:pass
    finally:
        if identifier:
            await asyncio.to_thread(bridge.call, 'official/ws/close', {'id': identifier})

def register_host(app):
    app.add_api_websocket_route('/api',serve_socket,name='hermes-official-realtime')
