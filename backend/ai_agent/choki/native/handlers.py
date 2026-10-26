"""Preserve all official endpoint semantics through the existing /api transport."""
from fastapi import APIRouter, HTTPException
from ai_agent.choki.engine.http_adapter import invoke
from fastapi.responses import Response
import base64
import json
import re
from urllib.parse import urlencode, urljoin

router = APIRouter(prefix='/api/ai_agent/choki/official')


@router.get('/catalog')
def catalog():
    return invoke('official/catalog')


@router.get('/info')
def info():
    return invoke('engine/info')


@router.post('/http')
def http(request: dict):
    return invoke('official/http', request)


@router.get('/asset')
def asset(path: str):
    value = invoke('official/http', {'path': path})
    content = base64.b64decode(value['body'])
    kind = value['headers'].get('content-type', 'application/octet-stream')
    if value['status'] == 200 and 'javascript' in kind:
        content = (b'(function(fetch,WebSocket){\n' + content +
                   b'\n})(window.HermesPlatform.fetch,window.HermesPlatform.WebSocket);\n')
    elif value['status'] == 200 and 'text/css' in kind:
        def resource(match):
            target = match.group(1).strip(' \"\'')
            if target.startswith(('data:', 'http:', 'https:', '#')): return match.group(0)
            operation = {'operation': 'ai_agent/choki/official/asset',
                         'payload': json.dumps({'path': urljoin(path, target)}, ensure_ascii=False)}
            return 'url("/api?' + urlencode(operation) + '")'
        content = re.sub(r'url\(([^)]+)\)', resource, content.decode('utf-8')).encode('utf-8')
    headers = {key:val for key,val in value['headers'].items()
               if key.lower() not in {'content-encoding','content-length','transfer-encoding','set-cookie','content-security-policy'}}
    headers['cache-control'] = 'no-cache'
    return Response(content, status_code=value['status'], headers=headers)


@router.post('/ws/{action}')
def websocket_message(action: str, request: dict):
    if action not in ('open', 'send', 'poll', 'close'):
        raise HTTPException(404, '등록되지 않은 실시간 통신 작업입니다.')
    return invoke('official/ws/' + action, request)
