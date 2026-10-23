"""Password gate for the public Tailscale Funnel address."""
from __future__ import annotations

import hashlib
import hmac
import html
import json
import ipaddress
import os
import secrets
import time
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from starlette.types import ASGIApp, Receive, Scope, Send


class RemoteAccessMiddleware:
    """Require one password on remote requests; local Mac use stays unchanged."""

    def __init__(self, app: ASGIApp, config_path: str):
        self.app = app
        try:
            config = json.loads(Path(config_path).read_text(encoding='utf-8'))
            self.password = str(config['password']).encode('utf-8')
            self.cookie_key = str(config['cookie_key']).encode('utf-8')
        except (OSError, KeyError, TypeError, ValueError):
            self.password = b''
            self.cookie_key = b''

    @staticmethod
    def _host(scope: Scope) -> str:
        headers = {key.lower(): value for key, value in scope.get('headers', [])}
        host = headers.get(b'host', b'').decode('latin1').lower().split(':', 1)[0]
        forwarded = headers.get(b'x-forwarded-host', b'').decode('latin1').lower().split(':', 1)[0]
        client = (scope.get('client') or ('', 0))[0]
        if forwarded.endswith('.ts.net') and client in ('127.0.0.1', '::1'):
            return forwarded
        return host

    def _is_public(self, scope: Scope) -> bool:
        host = self._host(scope)
        if host.endswith('.ts.net'):
            return True
        client = (scope.get('client') or ('', 0))[0]
        try:
            return not ipaddress.ip_address(client).is_loopback
        except ValueError:
            return True

    def _cookie(self, expires: str) -> str:
        signature = hmac.new(self.cookie_key, expires.encode(), hashlib.sha256).hexdigest()
        return f'{expires}.{signature}'

    def _authorized(self, scope: Scope) -> bool:
        if not self.password or not self.cookie_key:
            return False
        headers = {key.lower(): value for key, value in scope.get('headers', [])}
        cookies = headers.get(b'cookie', b'').decode('latin1').split(';')
        value = next((item.strip().partition('=')[2] for item in cookies
                      if item.strip().startswith('platform_access=')), '')
        expires, separator, signature = value.partition('.')
        if not separator or not expires.isdigit() or int(expires) < int(time.time()):
            return False
        return hmac.compare_digest(self._cookie(expires).partition('.')[2], signature)

    @staticmethod
    async def _respond(send: Send, status: int, body: bytes, headers=()) -> None:
        content_type = next((value for name, value in headers
                             if name.lower() == b'content-type'),
                            b'text/html; charset=utf-8')
        response_headers = [(name, value) for name, value in headers
                            if name.lower() != b'content-type']
        await send({'type': 'http.response.start', 'status': status,
                    'headers': [(b'content-type', content_type),
                                (b'content-length', str(len(body)).encode()),
                                (b'cache-control', b'no-store'), *response_headers]})
        await send({'type': 'http.response.body', 'body': body})

    @staticmethod
    def _login_page(next_url: str, error: bool = False) -> bytes:
        destination = html.escape(next_url, quote=True)
        message = '<p style="color:#b42318">비밀번호가 맞지 않습니다.</p>' if error else ''
        page = ('<!doctype html><html lang="ko"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>프로젝트 플랫폼 로그인</title>'
                '<body style="font:16px system-ui;max-width:380px;margin:15vh auto;padding:24px">'
                '<h1>프로젝트 플랫폼</h1><p>접속 비밀번호를 입력하세요.</p>' + message +
                '<form method="post" action="/__remote_login">'
                f'<input type="hidden" name="next" value="{destination}">'
                '<input name="password" type="password" required autofocus '
                'autocomplete="current-password" style="box-sizing:border-box;width:100%;padding:14px">'
                '<button style="margin-top:12px;padding:12px 20px">접속</button></form></body></html>')
        return page.encode('utf-8')

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] not in ('http', 'websocket') or not self._is_public(scope):
            await self.app(scope, receive, send)
            return
        if not self.cookie_key:
            if scope['type'] == 'websocket':
                await send({'type': 'websocket.close', 'code': 1011})
            else:
                await self._respond(send, 503, b'\xec\x9b\x90\xea\xb2\xa9 \xec\xa0\x91\xec\x86\x8d \xeb\xb9\x84\xeb\xb0\x80\xeb\xb2\x88\xed\x98\xb8\xea\xb0\x80 \xec\x84\xa4\xec\xa0\x95\xeb\x90\x98\xec\xa7\x80 \xec\x95\x8a\xec\x95\x98\xec\x8a\xb5\xeb\x8b\x88\xeb\x8b\xa4.')
            return
        path = scope.get('path', '/')
        if path == '/__remote_login' and scope['type'] == 'http':
            method = scope.get('method', 'GET').upper()
            query = dict((key, values[-1]) for key, values in
                         parse_qs(scope.get('query_string', b'').decode()).items())
            host = self._host(scope)
            next_url = self._safe_next(query.get('next', '/'), host)
            if method == 'POST':
                body = bytearray()
                while True:
                    message = await receive()
                    body.extend(message.get('body', b''))
                    if not message.get('more_body', False):
                        break
                form = parse_qs(body.decode('utf-8', errors='replace'))
                supplied = form.get('password', [''])[-1].encode('utf-8')
                posted_next = form.get('next', [next_url])[-1]
                next_url = self._safe_next(posted_next, host)
                if hmac.compare_digest(supplied, self.password):
                    expires = str(int(time.time()) + 30 * 24 * 60 * 60)
                    headers = {key.lower(): value for key, value in scope.get('headers', [])}
                    forwarded_proto = headers.get(b'x-forwarded-proto', b'').decode('latin1').lower()
                    secure = host.endswith('.ts.net') or forwarded_proto == 'https'
                    cookie = f'platform_access={self._cookie(expires)}; Path=/; Max-Age=2592000; HttpOnly; '
                    cookie += ('Secure; ' if secure else '') + 'SameSite=Lax'
                    await send({'type': 'http.response.start', 'status': 303,
                                'headers': [(b'location', next_url.encode('latin1', errors='ignore')),
                                            (b'set-cookie', cookie.encode()),
                                            (b'cache-control', b'no-store')]})
                    await send({'type': 'http.response.body', 'body': b''})
                    return
                await self._respond(send, 401, self._login_page(next_url, True))
                return
            await self._respond(send, 200, self._login_page(next_url),
                                [(b'content-security-policy', b"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")])
            return
        if self._authorized(scope):
            if scope['type'] == 'http':
                scope.setdefault('state', {})['remote_access_authenticated'] = True
            await self.app(scope, receive, send)
            return
        if scope['type'] == 'websocket':
            await send({'type': 'websocket.close', 'code': 4401})
            return
        if path.startswith('/api'):
            await self._respond(send, 401, b'{"detail":"\xeb\xb9\x84\xeb\xb0\x80\xeb\xb2\x88\xed\x98\xb8 \xec\x9e\x85\xeb\xa0\xa5\xec\x9d\xb4 \xed\x95\x84\xec\x9a\x94\xed\x95\xa9\xeb\x8b\x88\xeb\x8b\xa4."}',
                                [(b'content-type', b'application/json')])
            return
        query = scope.get('query_string', b'').decode('latin1')
        next_url = path + (f'?{query}' if query else '')
        location = '/__remote_login?next=' + quote(next_url, safe='/')
        await send({'type': 'http.response.start', 'status': 303,
                    'headers': [(b'location', location.encode()), (b'cache-control', b'no-store')]})
        await send({'type': 'http.response.body', 'body': b''})

    @staticmethod
    def _safe_next(value: str, host: str) -> str:
        """Allow a local path or this same Funnel host's Gateway port."""
        if value.startswith('/') and not value.startswith('//'):
            return value
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError:
            return '/'
        if (parsed.scheme == 'https' and parsed.hostname == host and port == 8443 and
                not parsed.username and not parsed.password):
            return value
        return '/'


def ensure_remote_access_config(path: Path) -> str:
    """Create the private password file once and return its password."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        config = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        config = {}
    password = str(config.get('password') or os.environ.get('PLATFORM_REMOTE_PASSWORD') or
                   secrets.token_urlsafe(12))
    cookie_key = str(config.get('cookie_key') or secrets.token_urlsafe(32))
    temporary = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    temporary.write_text(json.dumps({'password': password, 'cookie_key': cookie_key}) + '\n',
                         encoding='utf-8')
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    return password
