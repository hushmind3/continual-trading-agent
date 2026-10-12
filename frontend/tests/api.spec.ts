import {test, expect} from '@playwright/test';
import {request, apiUrl} from '../src/data/api';

test('a stalled request times out and the next request succeeds', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = ((_url, options) => new Promise((_resolve, reject) => {
    options?.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')), {once: true});
  })) as typeof fetch;
  try {
    await expect(request('state', {}, 'POST', 25)).rejects.toThrow('대기 시간이 초과');
    globalThis.fetch = (async () => new Response(JSON.stringify({connected: true}), {status: 200})) as typeof fetch;
    await expect(request('state')).resolves.toEqual({connected: true});
  } finally { globalThis.fetch = original; }
});

test('HTML server failures preserve HTTP status in the error', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = (async () => new Response('<html>failed</html>', {status: 500})) as typeof fetch;
  try { await expect(request('state')).rejects.toThrow('HTTP 500'); }
  finally { globalThis.fetch = original; }
});

test('JSON command failures retain the backend reason', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = (async () => new Response(JSON.stringify({detail: '작업이 실행 중입니다.'}), {status: 409})) as typeof fetch;
  try { await expect(request('train', {})).rejects.toThrow('작업이 실행 중입니다.'); }
  finally { globalThis.fetch = original; }
});

test('GET payloads use the same API envelope without losing special characters', () => {
  const url = new URL(apiUrl('state', {views: '["prices?symbol=^GSPC"]'}), 'http://127.0.0.1');
  expect(url.pathname).toBe('/api');
  expect(url.searchParams.get('operation')).toBe('state');
  expect(JSON.parse(url.searchParams.get('payload')!)).toEqual({views: '["prices?symbol=^GSPC"]'});
});
