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

test('REA displays partial native recovery counts in analysis and project explorer', async ({page}) => {
  const id='c'.repeat(32),project={id,name:'fixture.exe',kind:'file',artifact:'네이티브 바이너리',state:'saved',folder:'temporary fixture',created_at:'2026-10-14T00:00:00Z',original_files:1,inferred_files:2,function_total:2,decompiled_functions:1,unavailable_functions:1};
  await page.route('**/api*',async route=>{
    const request=route.request(),url=new URL(request.url());
    const envelope=request.method()==='GET'?{operation:url.searchParams.get('operation')}:request.postDataJSON();
    if(envelope?.operation==='rea/status'){await route.fulfill({json:{active:false,stage:'saved',detail:'저장 완료',project}});return;}
    if(envelope?.operation==='rea/pick'){await route.fulfill({json:{path:'temporary-fixture.exe'}});return;}
    if(envelope?.operation==='rea/analyze'){await route.fulfill({json:project});return;}
    if(envelope?.operation==='rea/projects'){await route.fulfill({json:{items:[project]}});return;}
    if(envelope?.operation==='rea/project/tree'){await route.fulfill({json:{items:[],path:''}});return;}
    await route.continue();
  });
  await page.goto('/#rea/program_analysis',{waitUntil:'networkidle'});
  await page.getByRole('button',{name:'파일 선택',exact:true}).click();
  await expect(page.locator('main')).toContainText('함수 2개 · 의사코드 복원 1개 · 복원 불가 1개');
  await page.getByRole('link',{name:'프로젝트 탐색',exact:true}).last().click();
  await expect(page.getByRole('combobox',{name:'저장 프로젝트 선택',exact:true})).toHaveValue(id);
  await expect(page.locator('main')).toContainText('함수 2개 · 의사코드 복원 1개 · 복원 불가 1개');
  await page.unrouteAll({behavior:'wait'});
});

test('REA resumes the visible analysis after navigation and stops polling when complete', async ({page}) => {
  const id='d'.repeat(32);let active=true,statusRequests=0;
  const project={id,input:'fixture.exe',name:'fixture.exe',kind:'file',state:'analyzing',folder:'temporary fixture',created_at:'2026-10-14T00:00:00Z',original_files:1,inferred_files:556,function_total:639,decompiled_functions:555,unavailable_functions:84};
  await page.route('**/api*',async route=>{
    const request=route.request(),url=new URL(request.url());
    const operation=request.method()==='GET'?url.searchParams.get('operation'):request.postDataJSON()?.operation;
    if(operation==='rea/status'){
      statusRequests++;await route.fulfill({json:{active,stage:active?'native-decompile':'saved',detail:active?'639개 함수의 의사코드를 복원하고 있습니다.':'로컬 저장 완료',project:{...project,state:active?'analyzing':'saved'}}});return;
    }
    await route.continue();
  });
  await page.goto('/#rea/program_analysis',{waitUntil:'networkidle'});
  await expect(page.getByRole('status')).toContainText('639개 함수');
  await expect(page.getByRole('button',{name:'파일 선택',exact:true})).toBeDisabled();
  await page.locator('aside a[href="#finance/operation_control"]').click();
  await page.locator('aside a[href="#rea/program_analysis"]').click();
  await expect(page.getByRole('status')).toContainText('639개 함수');
  active=false;
  await expect(page.locator('main')).toContainText('함수 639개 · 의사코드 복원 555개 · 복원 불가 84개');
  await expect(page.getByRole('button',{name:'파일 선택',exact:true})).toBeEnabled();
  const completed=statusRequests;await page.waitForTimeout(2100);
  expect(statusRequests).toBe(completed);
  await page.unrouteAll({behavior:'wait'});
});


test('Kiwoom history collection displays real completion state and stops polling',async({page})=>{
 let started=false,queries=0,runningQueries=0;
 await page.route('**/api*',async route=>{
  const req=route.request(),url=new URL(req.url()),body=req.method()==='POST'?req.postDataJSON():{};
  const operation=body?.operation??url.searchParams.get('operation');
  if(operation!=='price/history'){await route.continue();return;}
  if(req.method()==='POST')started=true;else queries++;
  const running=started&&req.method()==='GET'&&runningQueries++===0;
  const result={status:running||req.method()==='POST'?'running':'completed',rows:running?0:600,
   symbols:running?[]:[{symbol:'005930.KS',rows:600,start:'2024-04-22',end:'2026-10-13'}],errors:[]};
  await route.fulfill({json:result});
 });
 await page.goto('/#finance/policy_learning');
 await page.getByRole('button',{name:'키움 가격 수집',exact:true}).click();
 await expect.poll(()=>runningQueries).toBeGreaterThan(1);
 await page.getByText('수집 완료 · 600행 · 1종목',{exact:true}).waitFor();
 await page.getByText('실제 저장 범위',{exact:true}).click();
 await expect(page.getByText('005930.KS · 2024-04-22 ~ 2026-10-13 · 600행',{exact:true})).toBeVisible();
 const before=queries;await page.waitForTimeout(2400);expect(queries).toBe(before);
});

test('price timeframe reaches preflight and changing it invalidates training approval',async({page})=>{
 const requests:Array<{currency:string;timeframe:string}>=[];let trainCalls=0;
 await page.route('**/api*',async route=>{
  const req=route.request(),url=new URL(req.url()),body=req.method()==='POST'?req.postDataJSON():{};
  const operation=body?.operation??url.searchParams.get('operation');
  if(operation==='train'){trainCalls++;await route.fulfill({json:{message:'unexpected training request'}});return;}
  if(operation!=='preflight/train'){await route.continue();return;}
  requests.push(body.payload);
  await route.fulfill({json:{ok:true,errors:[],symbols:['005930.KS'],currency:'KRW',timeframe:body.payload.timeframe,mode:'새 학습',steps_per_run:1024}});
 });
 await page.goto('/#finance/policy_learning');
 await page.getByRole('combobox',{name:'학습 통화',exact:true}).selectOption('KRW');
 await page.getByRole('combobox',{name:'학습 가격 주기',exact:true}).selectOption('1m');
 await page.getByRole('button',{name:'실행 전 검사',exact:true}).click();
 await expect.poll(()=>requests.at(-1)?.timeframe).toBe('1m');
 expect(requests.at(-1)?.currency).toBe('KRW');
 const start=page.getByRole('button',{name:/새 학습 시작/});
 await expect(start).toBeEnabled();
 await page.getByRole('combobox',{name:'학습 가격 주기',exact:true}).selectOption('1d');
 await expect(start).toBeDisabled();
 expect(trainCalls).toBe(0);
});


test('MoE excludes stale selections and labels incomplete registrations honestly', async ({page}) => {
  await page.addInitScript(()=>sessionStorage.setItem('finrl-x.champion.selection',JSON.stringify(['removed_a','removed_b','chronos_bolt_tiny'])));
  await page.route('**/api',async route=>{
    if(route.request().postDataJSON()?.operation==='state'){
      const response=await route.fetch(),state=await response.json();
      const valid=state.experts.items.find((item:{id:string})=>item.id==='chronos_bolt_tiny');
      state.experts.items=[valid,{id:'q',representation:'INT4',package:{file:'source.bin',bytes:1,sha256:'known'},package_available:false,loaded:false,resources:{}}];
      await route.fulfill({response,json:state});return;
    }
    await route.continue();
  });
  await page.goto('/#finance/moe',{waitUntil:'networkidle'});
  await expect(page.getByRole('button',{name:'SAC MoE 생성 · 1개',exact:true})).toBeVisible();
  await expect(page.getByText('1개 모델 · 실패 기록 0개 선택',{exact:true})).toBeVisible();
  await expect(page.getByRole('tab',{name:'분류 미지정 1',exact:true})).toBeVisible();
  await expect(page.getByText('q',{exact:true})).toBeVisible();
  await expect(page.getByText('파일 없음 · 크기 미확인',{exact:true})).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('등록 JSON');
  await expect(page.getByRole('button',{name:'양자화',exact:true}).last()).toBeDisabled();
  expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('finrl-x.champion.selection')!))).toEqual(['chronos_bolt_tiny']);
});


test('operation screen separates feed execution from broker and quote reception', async ({page}) => {
  await page.route('**/api',async route=>{
    if(route.request().postDataJSON()?.operation==='state'){
      const response=await route.fetch(),state=await response.json();
      state.operations.controls.feed=true;
      state.operations.broker={connected:false,kr_connected:false,us_connected:false,transport_status:'reconnecting',reconnect_in_seconds:2,quote_events:0};
      await route.fulfill({response,json:state});return;
    }
    await route.continue();
  });
  await page.goto('/#finance/operation_control',{waitUntil:'networkidle'});
  const connection=page.getByRole('region',{name:'실제 시세 연결 상태'});
  await expect(connection).toContainText('연결 끊김 · 재연결 대기');
  await expect(connection).toContainText('국내 미연결');
  await expect(connection).toContainText('미국 미연결');
  await expect(connection).toContainText('실제 시세 수신 0건');
  await expect(connection).toContainText('2초 후 연결 재시도');
});


test('restored local Expert files appear in the real MoE list and detail drawer', async ({page,request}) => {
  const response=await request.post('/api',{data:{operation:'state',payload:{}}});
  const state=await response.json();
  for(const id of ['fincast','exaone','kronos','chronos','timesfm','timemoe','toto','stock_finrl_sac','qwen35_08b_gguf']){
    const item=state.experts.items.find((row:{id:string})=>row.id===id);
    expect(item?.package_available,id).toBe(true);
  }
  expect(state.experts.items.some((row:{id:string})=>row.id==='q')).toBe(false);
  await page.goto('/#finance/moe',{waitUntil:'networkidle'});
  await expect(page.getByText('등록 모델 '+state.experts.items.length+'개',{exact:true})).toBeVisible();
  await expect(page.getByText('FinCast 1.0B',{exact:true})).toBeVisible();
  await expect(page.getByText('unsloth/Qwen3.5-0.8B-GGUF',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:/^FinCast 1\.0B .*상세·검사 결과$/}).first().click();
  await expect(page.getByText(/market[\\/]FinCast[\\/]ORIGINAL\.pt/)).toBeVisible();
});
