import {test,expect} from '@playwright/test';

test('8766 serves the built React and current API on one origin',async({page,request})=>{
  const index=await request.get('http://127.0.0.1:8766/');
  expect(index.status()).toBe(200);
  const html=await index.text();
  expect(html).toContain('<div id="root">');
  expect(html).toMatch(/\/assets\/index-[^"]+\.js/);
  expect(html).not.toContain('/src/main.tsx');
  expect(html).not.toContain('streamlit');
  const assets=[...html.matchAll(/(?:src|href)="(\/assets\/[^"]+)"/g)].map(m=>m[1]);
  for(const asset of assets)expect((await request.get('http://127.0.0.1:8766'+asset)).status()).toBe(200);
  const health=await (await request.get('http://127.0.0.1:8766/api/health')).json();
  expect(health.service).toBe('finrlx-react-sac');
  await page.goto('http://127.0.0.1:8766/#learning');
  await expect(page.getByRole('heading',{name:'공식 SAC 실행',exact:true})).toBeVisible();
});

test('5173 is Vite development only and proxies the same 8766 backend',async({page,request})=>{
  const dev=await request.get('http://127.0.0.1:5173/');
  expect((await dev.text())).toContain('/src/main.tsx');
  const production=await (await request.get('http://127.0.0.1:8766/api/health')).json();
  const development=await (await request.get('http://127.0.0.1:5173/api/health')).json();
  expect(development.pid).toBe(production.pid);
  expect(development.project).toBe(production.project);
  await page.goto('http://127.0.0.1:5173/#portfolio');
  await expect(page.getByRole('heading',{name:'공식 BacktestEngine 평가',exact:true})).toBeVisible();
});

test('same-origin adapters accept 8766 requests and reject other origins',async({request})=>{
  const body={currency:'USD',symbols:['NOT_REGISTERED'],resume:false};
  const local=await request.post('http://127.0.0.1:8766/api/preflight/train',{
    data:body,headers:{Origin:'http://127.0.0.1:8766'}});
  expect(local.status()).toBe(200);
  expect((await local.json()).ok).toBe(false);
  const other=await request.post('http://127.0.0.1:8766/api/preflight/train',{
    data:body,headers:{Origin:'http://another-project.invalid'}});
  expect(other.status()).toBe(403);
  expect((await request.get('http://127.0.0.1:8766/api/does-not-exist')).status()).toBe(404);
});
