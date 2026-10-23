import { ServerResponse } from 'node:http';

const originalSetHeader = ServerResponse.prototype.setHeader;
const platformOrigins = (process.env.PLATFORM_EMBED_ORIGINS || 'http://127.0.0.1:8766')
  .split(',').map((origin) => origin.trim()).filter(Boolean);

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
