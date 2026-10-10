import {test,expect} from '@playwright/test';

test('restored white layout and seven menus call current SAC API',async({page})=>{
  const failures:string[]=[],paths=new Set<string>();
  page.on('pageerror',e=>failures.push(e.message));
  page.on('response',r=>{if(r.url().includes('/api/')){paths.add(new URL(r.url()).pathname);if(r.status()>=400)failures.push(r.status()+' '+r.url())}});
  await page.goto('/#control');
  await expect(page.getByText('공식 SAC 운영',{exact:true})).toBeVisible();
  for(const label of ['운영','MoE','시장','계좌','학습','연결','진단'])await expect(page.getByRole('navigation').getByRole('link',{name:label,exact:true})).toBeVisible();
  expect(await page.locator('.min-h-dvh').evaluate(e=>getComputedStyle(e).backgroundColor)).toBe('rgb(244, 246, 250)');
  for(const [route,heading] of [['moe','Expert 슬롯 관리'],['markets','시장 · 실제 가격 저장소'],['portfolio','공식 BacktestEngine 평가'],['learning','시장 경험으로 정책 가중치 업데이트'],['connection','연결 상태'],['system','현재 실행 프로세스']]){
    await page.goto('/#'+route);await expect(page.getByRole('heading',{name:heading,exact:true})).toBeVisible();
  }
  await expect(page.getByText('src/stockrl/framework.py',{exact:true})).toBeVisible();
  expect(paths.has('/api/state')).toBeTruthy();expect(paths.has('/api/connections')).toBeTruthy();
  expect(paths.has('/api/modules')).toBeTruthy();expect(paths.has('/api/logs')).toBeTruthy();
  expect(paths.has('/api/result/weights')).toBeTruthy();expect(failures).toEqual([]);
  await page.goto('/#control');await expect(page.getByText('공식 SAC 운영',{exact:true})).toBeVisible();
  await page.screenshot({path:'test-results/restored-white-desktop.png',fullPage:true});
});

test('SAC selection and real preflight gate start and reset on market change',async({page})=>{
  await page.goto('/#learning');
  const start=page.getByRole('button',{name:'SAC 새 학습 시작',exact:true});
  await expect(start).toBeDisabled();
  await page.getByRole('button',{name:'저장 정책 종목 선택',exact:true}).click();
  const response=page.waitForResponse(r=>r.url().endsWith('/api/preflight/train')&&r.status()===200);
  await page.getByRole('button',{name:'실행 전 검사',exact:true}).click();
  const checked=await (await response).json();expect(checked.symbols).toEqual(['AAPL','MSFT']);expect(checked.ok).toBe(true);
  await expect(start).toBeEnabled();
  let payload:unknown;
  await page.route('**/api/train',async route=>{payload=route.request().postDataJSON();await route.fulfill({json:{message:'검증용 요청 전달 확인 · 학습 실행 없음'}})});
  await start.click();await expect(page.getByText('검증용 요청 전달 확인 · 학습 실행 없음')).toBeVisible();
  expect(payload).toEqual({currency:'USD',symbols:['AAPL','MSFT'],resume:false});
  await page.getByLabel('학습 통화',{exact:true}).selectOption('KRW');await expect(start).toBeDisabled();
  await page.getByLabel('학습 종목 검색',{exact:true}).fill('삼성');
  await expect(page.getByRole('table',{name:'학습 종목'})).toContainText('005930.KS');
  await expect(page.getByRole('heading',{name:'Actor · Twin Critic · Target Critic'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'저장 정책 · 체크포인트'})).toBeVisible();
});

test('market history and transfer selection use actual DataStore',async({page})=>{
  await page.goto('/#markets');
  await page.getByLabel('시장 종목 검색',{exact:true}).fill('AAPL');
  await page.getByRole('button',{name:/^AAPL/}).first().click();
  const drawer=page.getByRole('dialog');await expect(drawer).toBeVisible();
  await expect(drawer.getByRole('table',{name:'OHLCV'})).toContainText('2025');
  await drawer.getByLabel('가격 조회 개수',{exact:true}).selectOption('100');
  await expect(drawer.getByText('100개 / 전체 100개',{exact:true})).toBeVisible();
  await drawer.getByRole('button',{name:'이 종목으로 학습 선택',exact:true}).click();
  await expect(page).toHaveURL(/#learning$/);
  await expect(page.getByLabel('AAPL 선택',{exact:true})).toBeChecked();
});

test('Expert family tabs, real inference details and registration form are restored',async({page})=>{
  await page.goto('/#moe');
  await page.getByRole('tab',{name:/^매매 판단/}).click();
  await expect(page.getByRole('button',{name:'FinCast 1.0B 상세',exact:true})).toHaveCount(0);
  await page.getByRole('tab',{name:/^시계열 예측/}).click();
  await page.getByRole('button',{name:'FinCast 1.0B 상세',exact:true}).click();
  await expect(page.getByRole('dialog').getByText('마지막 적재·RAM·VRAM 측정',{exact:true})).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'패키지 가져오기',exact:true}).click();
  await page.getByLabel('Expert 패키지 경로',{exact:true}).fill('C:/missing/package.pt');
  await page.getByLabel('Expert 슬롯 이름',{exact:true}).fill('test_frontend_missing');
  const response=page.waitForResponse(r=>r.url().endsWith('/api/experts/register')&&r.status()===400);
  await page.getByRole('button',{name:'패키지 등록',exact:true}).click();await response;
  await expect(page.getByRole('dialog').getByRole('alert')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByText('현재 실행 경로에서 제거',{exact:true}).first()).toBeVisible();
});

test('official replay and defaults are real, obsolete policy evaluation is blocked',async({page,request})=>{
  const snapshot=await (await request.get('/api/state')).json();
  expect(snapshot.architecture).toBe('finrlx-official-sac-v2');
  expect(snapshot.settings.policy.actor_arch).toEqual([256,256]);
  expect(snapshot.settings.policy.n_critics).toBe(2);
  expect(snapshot.settings.parameters.batch_size).toBe(128);
  expect(snapshot.settings.sb3_defaults.batch_size).toBe(256);
  expect(snapshot.model.replay_state.size).toBe(128);
  await page.goto('/#portfolio');
  const response=page.waitForResponse(r=>r.url().endsWith('/api/preflight/backtest')&&r.status()===200);
  await page.getByRole('button',{name:'평가 전 검사',exact:true}).click();
  const result=await (await response).json();expect(result.ok).toBe(false);
  await expect(page.getByRole('button',{name:'SAC 백테스트 실행',exact:true})).toBeDisabled();
  await expect(page.getByText(/이전 두 통화 가상계좌/)).toBeVisible();
  await page.getByRole('tab',{name:'백테스트 거래',exact:true}).click();
  await expect(page.getByText('저장된 내역이 없습니다.',{exact:true})).toBeVisible();
  expect((await request.get('/api/result/trades')).status()).toBe(200);
});

test('write endpoints reject invalid work without training or registry changes',async({request})=>{
  expect((await request.post('/api/train',{data:{currency:'USD',symbols:['NOT_REGISTERED'],resume:false}})).status()).toBe(400);
  expect((await request.post('/api/backtest',{data:{currency:'USD',symbols:['AAPL','MSFT'],resume:false}})).status()).toBe(400);
  expect((await request.post('/api/stop',{data:{}})).status()).toBe(409);
  expect((await request.post('/api/experts/select',{data:{active:['missing_slot']}})).status()).toBe(400);
  expect((await request.post('/api/collect',{data:{symbols:['NOT_REGISTERED'],start_date:'2026-01-01',end_date:'2026-01-10'}})).status()).toBe(400);
  const connections=await (await request.get('/api/connections')).json();
  expect(connections.brokers.every((r:{status:string})=>r.status==='not_connected')).toBeTruthy();
});

test('mobile layout preserves seven menus and avoids document overflow',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.goto('/#learning');
  await expect(page.getByRole('heading',{name:'공식 SAC 실행',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await page.getByRole('navigation').getByRole('link',{name:'MoE',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Expert 슬롯 관리',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await page.screenshot({path:'test-results/mobile-moe.png',fullPage:true});
});
