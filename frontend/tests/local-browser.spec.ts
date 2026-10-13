import {test, expect} from '@playwright/test';

test('all registered local screens render and continue receiving state', async ({page}, testInfo) => {
  test.setTimeout(240_000);
  const errors: string[] = [];
  const failures: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => {if (response.url().includes('/api') && response.status() >= 500) failures.push(`${response.status()} ${response.url()}`);});
  await page.goto('/', {waitUntil: 'networkidle'});
  await expect(page.getByText('서버 연결', {exact: true})).toBeVisible();
  await expect(page.locator('aside a[href="#rea/program_analysis"]')).toBeVisible();
  expect((await page.locator('aside details > summary').allTextContents()).map(text=>text.replace(/\s*오류\s*\d+\s*$/,'').trim())).toEqual(['금융','REA 역공학']);
  const links = await page.locator('aside a').evaluateAll(elements => elements
    .map(element => ({href: element.getAttribute('href') || '', name: element.textContent || ''}))
    .filter(element => element.href.startsWith('#')));
  const unique = [...new Map(links.map(link => [link.href, link])).values()];
  const response=await page.request.post('/api',{data:{operation:'state',payload:{views:JSON.stringify(['menu_catalog'])}}});
  expect(response.ok()).toBeTruthy();
  const catalog=await response.json();
  const nodes:unknown[]=[catalog.views.menu_catalog.data.groups],registered:string[]=[];
  while(nodes.length){const node=nodes.pop();if(Array.isArray(node)){nodes.push(...node);continue;}if(node&&typeof node==='object'){const row=node as Record<string,unknown>;if(typeof row.id==='string'&&typeof row.frontend==='string'&&row.frontend)registered.push('#'+row.id);nodes.push(...Object.values(row));}}
  expect(registered.length).toBeGreaterThan(0);
  expect(unique.map(link=>link.href).sort()).toEqual([...new Set(registered)].sort());
  const removed = ['markets','finrl-trading','feature-adaptive_download','feature-adaptive_single','feature-adaptive_backtest','feature-calendar','feature-config_check','portfolio','finrl','stock-training','backtest','feature-finrl_workflow','feature-yahoo','feature-features','feature-data_split','feature-finrl_stats','feature-fundamentals','feature-news','feature-nasdaq100','feature-sp500','feature-process_prices','feature-process_fundamentals','feature-ml_dataset','feature-tsmom','feature-adaptive','feature-equal_weight','feature-ml','feature-sector_ml','feature-performance'];
  expect(unique.filter(link => removed.includes(link.href.slice(1))).map(link => link.href)).toEqual([]);
  for (const link of unique) {
    await page.locator(`aside a[href="${link.href}"]`).click();
    await expect(page.locator('main h1')).toContainText(link.name.trim());
    await expect(page.locator('main')).not.toContainText('통합 API 연결:');
    await expect(page.locator('main')).not.toContainText('화면을 여는 중입니다.');
    await page.screenshot({path: testInfo.outputPath(`${link.href.slice(1)}.png`), fullPage: true});
  }
  expect(errors).toEqual([]);
  expect(failures).toEqual([]);
  console.log(`Verified ${unique.length} live local screens with screenshots, no JS crashes, no HTTP 500`);
});

test('model errors remain visible in MoE and diagnostics without becoming a transport error elsewhere', async ({page}) => {
  await page.route('**/api', async route => {
    const envelope = route.request().postDataJSON();
    if (envelope?.operation !== 'state') { await route.continue(); return; }
    const response = await route.fetch();
    const state = await response.json();
    state.module_errors = {...state.module_errors, 'champion:validation-only': '검증용 모델 형식 오류'};
    await route.fulfill({response, json: state});
  });
  await page.goto('/#finance/operation_control', {waitUntil: 'networkidle'});
  await expect(page.locator('main')).toContainText('다른 기능 오류');
  await expect(page.locator('main')).not.toContainText('검증용 모델 형식 오류');
  await expect(page.locator('main')).not.toContainText('통합 API 연결:');
  await page.locator('aside a[href="#finance/moe"]').click();
  await expect(page.locator('main')).toContainText('검증용 모델 형식 오류');
  await page.locator('aside a[href="#finance/diagnostics_logs_code_apply"]').click();
  await expect(page.locator('main')).toContainText('검증용 모델 형식 오류');
});

test('REA has three input buttons and browses real saved source files without agent controls', async ({page}) => {
  const errors:string[]=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/#rea/program_analysis',{waitUntil:'networkidle'});
  await expect(page.getByRole('button',{name:'파일 선택',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'폴더 선택',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'웹사이트 분석',exact:true}).click();
  await expect(page.getByRole('textbox',{name:'분석할 웹사이트 주소'})).toBeVisible();
  await expect(page.locator('main')).not.toContainText('도구 입력 JSON');
  await expect(page.locator('main')).not.toContainText('AI 재구성');
  await page.locator('aside a[href="#rea/project_explorer"]').click();
  await expect(page.getByRole('combobox',{name:'저장 프로젝트 선택'})).toBeVisible();
  const select=page.getByRole('combobox',{name:'저장 프로젝트 선택'});
  const value=await select.locator('option').evaluateAll(options=>options.map(option=>option as HTMLOptionElement).find(option=>option.value&&option.text.includes('저장 완료'))?.value);
  expect(value).toBeTruthy();
  await select.selectOption(value!);
  await page.getByRole('button',{name:'📄README.md',exact:true}).click();
  await expect(page.locator('main pre')).toContainText('original/');
  await expect(page.getByRole('button',{name:'저장 폴더 열기',exact:true})).toBeEnabled();
  expect(errors).toEqual([]);
});

test('MoE renders missing input metadata and ignores invalid saved UI state', async ({page}) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => {
    sessionStorage.setItem('finrl-x.champion.selection', '{broken');
    sessionStorage.setItem('finrl-x.champion.result', JSON.stringify({policy_spaces: {}}));
  });
  await page.route('**/api', async route => {
    const envelope = route.request().postDataJSON();
    if (envelope?.operation !== 'state') { await route.continue(); return; }
    const response = await route.fetch();
    const state = await response.json();
    for (const item of state.experts?.items ?? []) delete item.input;
    await route.fulfill({response, json: state});
  });
  await page.goto('/#finance/moe', {waitUntil: 'networkidle'});
  await expect(page.getByRole('heading', {name: 'Expert 슬롯 관리'})).toBeVisible();
  await expect(page.getByRole('group', {name: 'Champion 조립용 모델 버전'}).first()).toBeVisible();
  await expect(page.getByRole('button', {name: '금융 Expert 찾기', exact: true})).toBeVisible();
  expect(errors).toEqual([]);
});

test('project explorer keeps the latest file when earlier responses arrive late', async ({page}) => {
  const id='a'.repeat(32);
  let releaseOld:()=>void=()=>{};
  let finishOld:()=>void=()=>{};
  const oldFinished=new Promise<void>(resolve=>{finishOld=resolve});
  await page.route('**/api*', async route => {
    const request=route.request(),url=new URL(request.url());
    const envelope=request.method()==='GET'?{operation:url.searchParams.get('operation'),payload:JSON.parse(url.searchParams.get('payload')??'{}')}:request.postDataJSON();
    if(envelope?.operation==='rea/projects'){
      await route.fulfill({json:{items:[{id,name:'race fixture',folder:'temporary fixture',kind:'folder',state:'saved',created_at:'2026-10-14T00:00:00Z'}]}});return;
    }
    if(envelope?.operation==='rea/project/tree'){
      await route.fulfill({json:{path:'',items:[{name:'old.js',path:'old.js',folder:false},{name:'new.js',path:'new.js',folder:false}]}});return;
    }
    if(envelope?.operation==='rea/project/file'){
      const old=envelope.payload.path==='old.js';
      if(old)await new Promise<void>(resolve=>{releaseOld=resolve});
      await route.fulfill({json:{content:old?'OLD CONTENT':'LATEST CONTENT',bytes:14}});
      if(old)finishOld();return;
    }
    await route.continue();
  });
  await page.goto('/#rea/project_explorer?id='+id,{waitUntil:'networkidle'});
  await expect(page.getByRole('button',{name:'📄old.js',exact:true})).toBeVisible();
  const oldRequest=page.waitForRequest(request=>request.url().includes('/api')&&JSON.parse(new URL(request.url()).searchParams.get('payload')??'{}').path==='old.js');
  await page.getByRole('button',{name:'📄old.js',exact:true}).click();
  await oldRequest;
  await page.getByRole('button',{name:'📄new.js',exact:true}).click();
  await expect(page.locator('main pre')).toHaveText('LATEST CONTENT');
  releaseOld();await oldFinished;
  await expect(page.locator('main pre')).toHaveText('LATEST CONTENT');
});

test('paper order rejects fractional quantities before sending a request', async ({page}) => {
  let orders=0;
  await page.route('**/api', async route=>{
    const envelope=route.request().postDataJSON();
    if(envelope?.operation==='orders'){orders++;await route.fulfill({json:{price_source:'live'}});return;}
    if(envelope?.operation==='state'){
      const response=await route.fetch(),state=await response.json();
      state.data.instruments=[...state.data.instruments.filter((item:{symbol:string})=>item.symbol!=='QUANTITY_FIXTURE'),{symbol:'QUANTITY_FIXTURE',name:'수량 검사',currency:'USD',eligible:true}];
      await route.fulfill({response,json:state});return;
    }
    await route.continue();
  });
  await page.goto('/#finance/virtual_account_orders',{waitUntil:'networkidle'});
  await page.getByRole('combobox',{name:'종목',exact:true}).selectOption('QUANTITY_FIXTURE');
  await page.getByRole('spinbutton',{name:'수량',exact:true}).fill('1.5');
  await expect(page.getByRole('button',{name:'가상 매수',exact:true})).toBeDisabled();
  await expect(page.getByRole('button',{name:'가상 매도',exact:true})).toBeDisabled();
  await expect(page.getByRole('alert')).toContainText('정수');
  expect(orders).toBe(0);
  await page.getByRole('spinbutton',{name:'수량',exact:true}).fill('1');
  await expect(page.getByRole('button',{name:'가상 매수',exact:true})).toBeEnabled();
});

test('native runner preserves JSON-looking strings and rejects array argument objects', async ({page}) => {
  const submitted:Record<string,unknown>[]=[];
  await page.route('**/api',async route=>{
    const envelope=route.request().postDataJSON();
    if(envelope?.operation==='framework/native_call'){
      submitted.push(envelope.payload);await route.fulfill({json:{message:'fixture accepted',job:{id:'fixture',running:false}}});return;
    }
    if(envelope?.operation==='state'){
      const response=await route.fetch(),state=await response.json();
      const catalog=state.views?.framework?.data;
      if(catalog){
        const original=catalog.items.find((item:{native_api?:string;framework:string})=>item.native_api&&item.framework==='FinRL');
        if(original)catalog.items=[{...original,id:'FinRL:fixture',path:'fixture.py',functions:['combine'],signatures:{combine:'value: str'},parameters:{combine:[{name:'value',annotation:'str',required:true}]}}];
      }
      await route.fulfill({response,json:state});return;
    }
    await route.continue();
  });
  await page.goto('/#finance/all_backend_features',{waitUntil:'networkidle'});
  await page.getByRole('tab',{name:'원본 모듈 · 함수',exact:true}).click();
  await expect(page.getByRole('combobox',{name:'원형 모듈',exact:true})).toHaveValue('FinRL:fixture');
  const raw=page.getByRole('textbox',{name:'원본 함수 인자',exact:true});
  await expect(raw).toBeVisible();
  await raw.fill('[]');
  await page.getByRole('button',{name:'원본 함수 실행',exact:true}).click();
  await expect(page.locator('main')).toContainText('함수·생성자 인자는 JSON 객체로 입력하세요.');
  expect(submitted).toHaveLength(0);
  await raw.fill('{}');
  await page.getByLabel(/value.*필수/).fill('{"keep":"literal"}');
  await page.getByRole('button',{name:'원본 함수 실행',exact:true}).click();
  await expect.poll(()=>submitted.length).toBe(1);
  expect(submitted[0].kwargs).toEqual({value:'{"keep":"literal"}'});
  await expect(page.getByRole('button',{name:'원본 함수 실행',exact:true})).toBeEnabled();
  await page.unrouteAll({behavior:'wait'});
});
