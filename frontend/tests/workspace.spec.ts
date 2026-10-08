import {test,expect} from '@playwright/test';

test('all operating routes, history and direct refresh use the served application',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#control');await expect(page.getByText('실시간 운영',{exact:true})).toBeVisible();
 for(const [name,hash] of [['MoE','moe'],['시장','markets'],['계좌','portfolio'],['학습','learning'],['연결','connection'],['진단','system'],['운영','control']]){
  await page.getByRole('navigation').getByRole('link',{name,exact:true}).click();
  await expect(page).toHaveURL(new RegExp(`#${hash}$`));await expect(page.getByRole('heading',{name,exact:true,level:1})).toBeVisible();
  await page.reload();await expect(page.getByRole('heading',{name,exact:true,level:1})).toBeVisible();
 }
 await page.goBack();await expect(page.getByRole('heading',{name:'진단',exact:true,level:1})).toBeVisible();
 await page.goForward();await expect(page.getByRole('heading',{name:'운영',exact:true,level:1})).toBeVisible();
 expect(errors).toEqual([]);
});

test('legacy hashes resolve immediately to the relevant current workspace',async({page})=>{
 for(const [hash,title] of [['assembly','MoE'],['experts','MoE'],['trading-moe','계좌'],['promotionTrial','학습']]){
  await page.goto(`/#${hash}`);await expect(page.getByRole('heading',{name:title,exact:true,level:1})).toBeVisible();
 }
});

test('market rows select with keyboard and close without losing focus',async({page})=>{
 await page.goto('/#markets');const row=page.locator('tbody tr').first();await expect(row).toBeVisible();
 await row.focus();await page.keyboard.press('Enter');await expect(page.getByRole('dialog')).toBeVisible();
 await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);await expect(row).toBeFocused();
 await row.click();await expect(page.getByRole('dialog')).toBeVisible();
});

test('expert rows open the selected original asset',async({page})=>{
 await page.goto('/#moe');const row=page.getByRole('button').filter({hasText:'FinCast'}).first();await expect(row).toBeVisible();
 await row.click();await expect(page.getByRole('dialog')).toBeVisible();await expect(page.getByText('원본 가중치 고정',{exact:true})).toBeVisible();
});

test('narrow layout exposes all navigation and stays within the viewport',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 for(const hash of ['control','moe','markets','portfolio','learning','connection','system']){
  await page.goto(`/#${hash}`);await expect(page.getByRole('navigation').getByRole('link')).toHaveCount(7);
  await page.waitForTimeout(600);
  const width=await page.evaluate(()=>({page:document.documentElement.scrollWidth,viewport:innerWidth}));expect(width.page).toBeLessThanOrEqual(width.viewport+1);
 }
});

test('opening notifications acknowledges only the displayed event watermark',async({page,request})=>{
 await page.goto('/#control');await expect(page.getByText('서버 연결',{exact:true})).toBeVisible();
 const response=page.waitForResponse(r=>r.url().endsWith('/api/events/read')&&r.request().method()==='POST');
 await page.getByRole('button',{name:/^알림 \d+개$/}).click();
 const read=await response;expect(read.ok()).toBeTruthy();
 const through=read.request().postDataJSON().through;
 await expect(page.getByRole('dialog')).toBeVisible();
 const snapshot=await (await request.get('/api/state')).json();
 expect(snapshot.events.filter((e:{id:number;read:boolean})=>e.id<=through&&!e.read)).toEqual([]);
});

test('paper control changes actual backend state and restores its previous setting',async({page,request})=>{
 const initial=await (await request.get('/api/state')).json();
 test.skip(!initial.controls.engine,'MoE must be running to exercise paper control');
 expect(initial.real_orders_enabled).toBe(false);
 const previous=initial.controls.paper;
 try{
  await page.goto('/#portfolio');
  await page.getByRole('button',{name:previous?'두 계좌 가상체결 정지':'두 계좌 가상체결 시작',exact:true}).click();
  await expect(page.getByRole('button',{name:previous?'두 계좌 가상체결 시작':'두 계좌 가상체결 정지',exact:true})).toBeVisible();
  const changed=await (await request.get('/api/state')).json();
  expect(changed.controls.paper).toBe(!previous);
  expect(changed.controls.feed).toBe(initial.controls.feed);
  expect(changed.controls.engine).toBe(initial.controls.engine);
 }finally{
  const restored=await request.post('/api/controls/paper',{data:{enabled:previous}});
  expect(restored.ok()).toBeTruthy();
 }
});

test('portfolio keeps Korean and US ledgers distinct and exposes missing history',async({page,request})=>{
 await page.goto('/#portfolio');
 await page.getByRole('tab',{name:'미국주식 · USD',exact:true}).click();
 await expect(page.getByRole('heading',{name:'미국주식 · 달러 가상계좌',exact:true})).toBeVisible();
 await page.getByRole('tab',{name:'체결 원장',exact:true}).click();
 await expect(page.getByText('미국주식 · 달러 가상계좌 체결 원장',{exact:true})).toBeVisible();
 const usd=await (await request.get('/api/fills?currency=USD')).json();
 expect(usd.fills.every((f:{currency:string})=>f.currency==='USD')).toBeTruthy();
 if(usd.missing)await expect(page.getByText(/이전 체결 .*기존 공용 기록이 삭제/)).toBeVisible();
 await page.getByRole('tab',{name:'국내주식 · KRW',exact:true}).click();
 await expect(page.getByRole('heading',{name:'국내주식 · 원화 가상계좌',exact:true})).toBeVisible();
 await expect(page.getByText('국내주식 · 원화 가상계좌 체결 원장',{exact:true})).toBeVisible();
 const krw=await (await request.get('/api/fills?currency=KRW')).json();
 expect(krw.fills.every((f:{currency:string})=>f.currency==='KRW')).toBeTruthy();
 if(krw.recorded>50){await expect(page.locator('tbody tr')).toHaveCount(50);await page.getByRole('button',{name:'이전 체결 더 보기'}).click();await expect(page.locator('tbody tr')).toHaveCount(100)}
});

test('position rows select the holding with keyboard',async({page})=>{
 await page.goto('/#portfolio');await page.getByRole('tab',{name:'국내주식 · KRW',exact:true}).click();
 const row=page.locator('tbody tr').first();await expect(row).toBeVisible();await row.focus();await page.keyboard.press('Enter');
 await expect(page.getByRole('dialog')).toBeVisible();await page.keyboard.press('Escape');await expect(row).toBeFocused();
});
