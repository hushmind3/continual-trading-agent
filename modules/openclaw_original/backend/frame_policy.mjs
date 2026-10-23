import { Server, ServerResponse } from 'node:http';
import { createHmac, timingSafeEqual } from 'node:crypto';
import { readFileSync, statSync } from 'node:fs';

const originalSetHeader = ServerResponse.prototype.setHeader;
const platformOrigins = (process.env.PLATFORM_EMBED_ORIGINS || 'http://127.0.0.1:8766')
  .split(',').map((origin) => origin.trim()).filter(Boolean);
let remoteCookieKey = '';
let remoteCookieConfigMtime = -1;
function reloadRemoteCookieKey() {
  try {
    const path = process.env.PLATFORM_REMOTE_ACCESS_FILE;
    const modified = statSync(path).mtimeMs;
    if (modified === remoteCookieConfigMtime) return;
    remoteCookieKey = JSON.parse(readFileSync(path, 'utf8')).cookie_key || '';
    remoteCookieConfigMtime = modified;
  } catch {
    remoteCookieKey = '';
    remoteCookieConfigMtime = -1;
  }
}

function hasRemoteCookie(request) {
  reloadRemoteCookieKey();
  if (!remoteCookieKey) return false;
  const value = request.headers.cookie?.split(';')
    .map((part) => part.trim()).find((part) => part.startsWith('platform_access='))
    ?.slice('platform_access='.length) || '';
  const separator = value.indexOf('.');
  if (separator < 1) return false;
  const expires = value.slice(0, separator);
  const supplied = Buffer.from(value.slice(separator + 1));
  if (!/^\d+$/.test(expires) || Number(expires) < Date.now() / 1000) return false;
  const expected = Buffer.from(createHmac('sha256', remoteCookieKey).update(expires).digest('hex'));
  return supplied.length === expected.length && timingSafeEqual(supplied, expected);
}

function requireRemoteLogin(request, responseOrSocket, isUpgrade = false) {
  const hostHeader = request.headers.host || '';
  let url;
  try { url = new URL(`https://${hostHeader}${request.url || '/'}`); } catch { return false; }
  if (!url.hostname.endsWith('.ts.net') || hasRemoteCookie(request)) return false;
  const next = `https://${url.host}${url.pathname}${url.search}`;
  const login = new URL('/__remote_login', `https://${url.hostname}`);
  login.searchParams.set('next', next);
  if (isUpgrade) {
    responseOrSocket.end('HTTP/1.1 401 Unauthorized\r\nConnection: close\r\n\r\n');
  } else {
    responseOrSocket.writeHead(303, { Location: login.toString(), 'Cache-Control': 'no-store' });
    responseOrSocket.end();
  }
  return true;
}

const originalEmit = Server.prototype.emit;
Server.prototype.emit = function (event, request, socket, head) {
  if ((event === 'request' || event === 'upgrade') && request &&
      requireRemoteLogin(request, socket, event === 'upgrade')) {
    return true;
  }
  return originalEmit.call(this, event, request, socket, head);
};

ServerResponse.prototype.setHeader = function (name, value) {
  const request = this.req;
  const pathname = request?.url?.split('?', 1)[0];
  const isControlUiDocument =
    pathname && !pathname.startsWith('/api/') && !pathname.startsWith('/__openclaw__/') &&
    request?.headers?.accept?.includes('text/html');

  if (isControlUiDocument && name.toLowerCase() === 'x-frame-options') {
    return this;
  }
  if (isControlUiDocument && name.toLowerCase() === 'content-security-policy' && typeof value === 'string') {
    const ancestors = `frame-ancestors ${platformOrigins.join(' ')}`;
    value = /frame-ancestors\s+[^;]+/i.test(value)
      ? value.replace(/frame-ancestors\s+[^;]+/i, ancestors)
      : `${value}; ${ancestors}`;
  }
  return originalSetHeader.call(this, name, value);
};
