import {test,expect,type Page} from '@playwright/test';
import {createServer} from 'node:http';
import {resolve} from 'node:path';

const origin='http://127.0.0.1:8766';
function envelope(request:any){
  if(request.method()==='GET')return {operation:new URL(request.url()).searchParams.get('operation')};
  return request.postDataJSON();
}
async function rejectWrites(page:Page,seen:string[]){
  await page.route('**/api*',async route=>{
    const request=route.request(),body=envelope(request);
    if(request.method()!=='GET'&&body?.operation!=='state'&&body?.operation!=='preflight/train'){
      seen.push(body.operation);
      await route.fulfill({status:400,json:{detail:'버튼 검사: '+body.operation}});
    }else await route.continue();
  });
}

test('trained Champion selection pins resume checkpoint and currency changes revoke approval',async({page})=>{
  const seen:string[]=[];await rejectWrites(page,seen);
  await page.goto('/#finance/policy_learning');
  const selection=page.getByRole('combobox',{name:'MoE Champion 선택',exact:true});
  await expect.poll(()=>selection.locator('option').count()).toBeGreaterThan(1);
  const trained=await selection.locator('option').evaluateAll(nodes=>nodes.map(n=>({value:(n as HTMLOptionElement).value,text:n.textContent??''})).find(n=>n.text.includes('이어 학습')));
  expect(trained).toBeTruthy();await selection.selectOption(trained!.value);
  await expect(page.getByRole('combobox',{name:'학습 방식',exact:true})).toHaveValue('resume');
  const response=page.waitForResponse(r=>envelope(r.request())?.operation==='preflight/train');
  await page.getByRole('button',{name:'실행 전 검사',exact:true}).click();
  const checked=await response,body=checked.request().postDataJSON().payload;
  expect(checked.status()).toBe(200);expect((await checked.json()).ok).toBe(true);
  expect(body.resume).toBe(true);expect(body.champion_path).toBe(trained!.value);expect(body.checkpoint).toBeTruthy();
  const start=page.getByRole('button',{name:/이어 학습 시작/});await expect(start).toBeEnabled();
  const dispatched=page.waitForRequest(r=>envelope(r)?.operation==='train');await start.click();
  expect((await dispatched).postDataJSON().payload).toEqual(body);
  await expect(page.getByText('버튼 검사: train',{exact:true})).toBeVisible();
  await page.getByRole('combobox',{name:'학습 통화',exact:true}).selectOption(body.currency==='KRW'?'USD':'KRW');
  await expect(selection).toHaveValue('');await expect(page.getByRole('button',{name:/새 학습 시작/})).toBeDisabled();
  expect(seen).toEqual(['train']);
});

test('operation buttons dispatch their own control and recover from rejected requests',async({page})=>{
  const seen:string[]=[];await rejectWrites(page,seen);await page.goto('/#finance/operation_control');
  const actions=[['자동 운영 시작','system/start'],['운영 중지','system/stop'],['시세 수신 시작','controls/feed'],['가상매매 켜기','controls/paper'],['SAC 자동 판단 켜기','controls/engine'],['실시간 SAC 지속학습 켜기','controls/learning']];
  for(const [label,operation] of actions){const button=page.getByRole('button',{name:label,exact:true});await expect(button).toBeEnabled();await button.click();await expect(page.getByText('버튼 검사: '+operation,{exact:true})).toBeVisible();await expect(button).toBeEnabled();}
  expect(seen).toEqual(actions.map(row=>row[1]));
});

test('connection and settings buttons dispatch without changing credentials or settings',async({page})=>{
  const seen:string[]=[];await rejectWrites(page,seen);await page.goto('/#finance/connection_settings');
  await page.getByRole('button',{name:'연결 확인',exact:true}).click();
  for(const [label,operation] of [['인증 후 저장·선택','provider/connect'],['저장된 키 인증 확인','provider/test'],['시세 연결 해제','provider/disconnect'],['공개 시세 선택','provider/public'],['운영 설정 저장','settings']]){
    const button=page.getByRole('button',{name:label,exact:true});await expect(button).toBeEnabled();await button.click();await expect(page.getByText('버튼 검사: '+operation,{exact:true})).toBeVisible();await expect(button).toBeEnabled();
  }
  expect(seen).toContain('settings');
});

test('MoE assembly ignores removed stock picker state and protected actions surface failures',async({page})=>{
  await page.addInitScript(()=>sessionStorage.setItem('training_symbols','broken legacy state'));
  const seen:string[]=[];await rejectWrites(page,seen);await page.goto('/#finance/moe');
  const create=page.getByRole('button',{name:/SAC MoE 생성/});await expect(create).toBeEnabled();
  const request=page.waitForRequest(r=>envelope(r)?.operation==='champions/create');await create.click();
  expect((await request).postDataJSON().payload).not.toHaveProperty('symbols');
  await expect(page.getByText('버튼 검사: champions/create',{exact:true})).toBeVisible();
  for(const [label,operation] of [['모델 폴더','model/open-directory'],['전체 Expert 실행 검사','library/probe_all'],['전체 양자화','library/quantize_all']]){
    await page.getByRole('button',{name:label,exact:true}).click();await expect(page.getByText('버튼 검사: '+operation,{exact:true})).toBeVisible();
  }
  await page.getByRole('button',{name:'금융 Expert 찾기',exact:true}).click();
  await page.getByRole('button',{name:'금융 Expert 자동 검색',exact:true}).click();await expect(page.getByText('버튼 검사: library/search',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'닫기',exact:true}).last().click();
  await page.getByRole('button',{name:'패키지 가져오기',exact:true}).click();
  await expect(page.getByRole('button',{name:'파일 구성 확인',exact:true})).toBeDisabled();
});

test('account tabs and order buttons send selected currency, side and whole-share quantity',async({page})=>{
  const seen:string[]=[];await rejectWrites(page,seen);await page.goto('/#finance/virtual_account_orders');
  for(const [tab,currency] of [['미국주식 · USD','USD'],['국내주식 · KRW','KRW']]){
    await page.getByRole('tab',{name:tab,exact:true}).click();
    const select=page.locator('main select');await expect.poll(()=>select.locator('option').count()).toBeGreaterThan(1);
    const symbol=await select.locator('option').nth(1).getAttribute('value');await select.selectOption(symbol!);
    for(const [label,action] of [['가상 매수','BUY'],['가상 매도','SELL']]){
      const request=page.waitForRequest(r=>envelope(r)?.operation==='orders');await page.getByRole('button',{name:label,exact:true}).click();
      expect((await request).postDataJSON().payload).toEqual({symbol,currency,action,quantity:1});await expect(page.getByText('버튼 검사: orders',{exact:true})).toBeVisible();
    }
    await page.getByRole('tab',{name:'가상체결 원장',exact:true}).click();await expect(page.getByRole('textbox',{name:'가상 체결 검색',exact:true})).toBeVisible();
    await page.getByRole('tab',{name:'보유 종목',exact:true}).click();await expect(page.getByRole('textbox',{name:'가상계좌 보유 검색',exact:true})).toBeVisible();
  }
});

test('clipboard failure is visible and diagnostics apply buttons recover',async({page})=>{
  await page.addInitScript(()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:()=>Promise.reject(new Error('clipboard denied'))}}));
  const seen:string[]=[];await rejectWrites(page,seen);await page.goto('/#finance/diagnostics_logs_code_apply');
  await page.getByRole('button',{name:'로그 복사',exact:true}).click();await expect(page.getByText('로그 복사 실패: clipboard denied',{exact:true})).toBeVisible();
  for(const label of ['프론트 적용','백엔드 적용']){await page.getByRole('button',{name:label,exact:true}).click();await expect(page.getByText('버튼 검사: system/apply',{exact:true})).toBeVisible();}
  await page.getByRole('button',{name:'로그 갱신',exact:true}).click();
});

test('REA file, folder and website buttons save real source and explorer reads it',async({page})=>{
  test.setTimeout(120_000);
  const file=resolve('src/pages/rea/program_analysis/README.md'),folder=resolve('src/pages/rea/program_analysis');
  const server=createServer((req,res)=>{res.setHeader('Content-Type',req.url==='/app.js'?'text/javascript':'text/html');res.end(req.url==='/app.js'?'function buttonExample(){return "source extraction";}':'<!doctype html><title>REA button example</title><h1>button example</h1><script src="/app.js"></script>');});
  await new Promise<void>(done=>server.listen(0,'127.0.0.1',done));
  const address=server.address() as {port:number};let pickKind='file';
  await page.route('**/api*',async route=>{const body=envelope(route.request());if(body?.operation==='rea/pick'){pickKind=route.request().postDataJSON().payload.kind;await route.fulfill({json:{path:pickKind==='file'?file:folder}});}else await route.continue();});
  try{
    for(const label of ['파일 선택','폴더 선택','웹사이트 분석']){
      const savedResponse=page.waitForResponse(r=>envelope(r.request())?.operation==='rea/analyze',{timeout:90_000});
      await page.goto('/#rea/program_analysis');await page.getByRole('button',{name:label,exact:true}).click();
      if(label==='웹사이트 분석'){await page.getByRole('textbox',{name:'분석할 웹사이트 주소',exact:true}).fill(`http://127.0.0.1:${address.port}`);await page.getByRole('button',{name:'소스 추출',exact:true}).click();}
      const response=await savedResponse;expect(response.status()).toBe(200);expect((await response.json()).original_files).toBeGreaterThan(0);
      await expect(page.getByRole('button',{name:'로컬 폴더에 저장했습니다.',exact:true})).toBeVisible({timeout:90_000});
      await page.getByRole('link',{name:'프로젝트 탐색',exact:true}).last().click();
      await page.getByRole('button',{name:'목록 새로고침',exact:true}).click();
      await page.getByRole('button',{name:/📁original/}).click();
      await expect(page.getByRole('button',{name:'상위 폴더',exact:true})).toBeVisible();
      const files=page.getByRole('button',{name:/📄/});
      for(let depth=0;depth<5;depth++){
        await expect.poll(async()=>await files.count()+await page.getByRole('button',{name:/📁/}).count()).toBeGreaterThan(0);
        if(await files.count())break;
        await page.getByRole('button',{name:/📁/}).first().click();
      }
      await expect(files.first()).toBeVisible();await files.first().click();await expect(page.locator('main pre')).not.toBeEmpty();
      await page.getByRole('button',{name:'상위 폴더',exact:true}).click();await page.getByRole('button',{name:'프로젝트 루트',exact:true}).click();
    }
  }finally{await new Promise<void>(done=>server.close(()=>done()));}
});

test('all registered menu panels, tabs, refresh and table pagination controls work',async({page})=>{
  page.setDefaultTimeout(5000);
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/#finance/operation_control');
  const links=page.locator('aside a[href^="#"]');await expect(links).toHaveCount(9);
  const paths=await links.evaluateAll(nodes=>nodes.map(node=>({path:node.getAttribute('href')!,name:node.textContent??''})));
  let panels=0;
  for(const {path,name} of paths){
    await page.goto('/'+path);await expect(page.locator('main h1')).toHaveText(name);
    await expect(page.locator('main button,main [role="tab"]').first()).toBeVisible();
    const collapsed=page.locator('main button[aria-expanded="false"]').filter({visible:true});
    while(await collapsed.count())await collapsed.first().click();
    const ids=await page.locator('main button[aria-expanded]').filter({visible:true}).evaluateAll(nodes=>nodes.map(node=>node.getAttribute('aria-controls')));
    for(const id of ids){
      const button=page.locator(`main button[aria-controls="${id}"]`);
      await button.click();await expect(button).toHaveAttribute('aria-expanded','false');await button.click();await expect(button).toHaveAttribute('aria-expanded','true');panels++;
    }
    for(const tab of await page.getByRole('tab').all()){await tab.click();await expect(tab).toHaveAttribute('aria-selected','true');}
    for(const input of await page.locator('main input[aria-label$="검색"]').all()){if(await input.isVisible()){await input.fill('button-audit-no-match');await input.fill('');}}
    for(const next of await page.getByRole('button',{name:'다음',exact:true}).all()){
      if(await next.isVisible()&&await next.isEnabled()){await next.click();await next.locator('..').getByRole('button',{name:'이전',exact:true}).click();}
    }
    await page.getByRole('button',{name:'새로고침',exact:true}).click();
  }
  await page.getByRole('button',{name:'메뉴 접기',exact:true}).click();await expect(page.getByRole('button',{name:'메뉴 펼치기',exact:true})).toHaveAttribute('aria-expanded','false');
  await page.getByRole('button',{name:'메뉴 펼치기',exact:true}).click();await page.getByRole('button',{name:/^알림 \d+개$/}).click();await expect(page.getByRole('dialog',{name:'현재 실행 · 알림',exact:true})).toBeVisible();await page.getByRole('button',{name:'닫기',exact:true}).last().click();
  expect(panels).toBeGreaterThan(20);expect(errors).toEqual([]);
});

test('backend catalog switches tabs and queries a real registered API',async({page})=>{
  await page.goto('/#finance/all_backend_features');
  await page.getByRole('button',{name:'소속 API · 입력값 보기',exact:true}).first().click();
  await expect(page.getByRole('tab',{name:'등록된 API · 입력값',exact:true})).toHaveAttribute('aria-selected','true');
  await page.getByRole('combobox',{name:'작은 메뉴 선택',exact:true}).selectOption('');
  const api=page.getByRole('combobox',{name:'API 선택',exact:true});await api.selectOption({label:'health · GET'});
  const response=page.waitForResponse(r=>envelope(r.request())?.operation==='health');
  await page.getByRole('button',{name:'선택 API 조회',exact:true}).click();
  const actual=await response;expect(actual.status()).toBe(200);await expect(page.locator('main pre').last()).toContainText(Object.keys(await actual.json())[0]);
  await page.getByRole('tab',{name:'원본 모듈 · 함수',exact:true}).click();await expect(page.getByRole('button',{name:'원본 함수 실행',exact:true})).toBeVisible();
  await page.getByRole('tab',{name:'큰 메뉴 · 전체 기능',exact:true}).click();
});

test('REA native chooser can be cancelled from the frontend and immediately used again',async({page})=>{
  await page.goto('/#rea/program_analysis');
  for(const label of ['파일 선택','폴더 선택']){
    const response=page.waitForResponse(r=>envelope(r.request())?.operation==='rea/pick');
    await page.getByRole('button',{name:label,exact:true}).click();
    await expect.poll(async()=>{const r=await page.request.get('/api?operation=rea/status');return (await r.json()).stage;}).toBe('picking');
    await page.getByRole('button',{name:'선택 취소',exact:true}).click();
    const cancelled=await response;expect(cancelled.status()).toBe(200);expect(await cancelled.json()).toEqual({path:''});
    await expect(page.getByRole('button',{name:label,exact:true})).toBeEnabled();
  }
});

test('MoE selected operations, version details and removal dispatch only chosen items',async({page})=>{
  const seen:string[]=[];await rejectWrites(page,seen);await page.goto('/#finance/moe');
  await page.getByRole('button',{name:'선택 해제',exact:true}).click();
  await page.getByRole('group',{name:'Champion 조립용 모델 버전',exact:true}).getByRole('checkbox').first().check();
  const operation=page.getByRole('combobox',{name:'선택 Expert 실행 작업',exact:true});
  for(const action of ['apply','probe_all','load','unload','compare','convert','optimize','optimize_all']){
    await operation.selectOption(action);await page.getByRole('button',{name:'선택 작업 실행',exact:true}).click();
    await expect(page.getByText('버튼 검사: '+(action==='apply'?'experts/select':'library/'+action),{exact:true})).toBeVisible();
  }
  for(const detail of await page.getByRole('button',{name:/상세·검사 결과$/}).all()){
    await detail.click();await expect(page.getByRole('dialog')).toBeVisible();await page.getByRole('button',{name:'닫기',exact:true}).last().click();
  }
  const remove=page.getByRole('button',{name:'선택 버전 삭제',exact:true}).filter({visible:true});
  for(const button of await remove.all()){if(await button.isEnabled()){await button.click();await expect(page.getByText('버튼 검사: library/remove',{exact:true})).toBeVisible();}}
  await page.getByRole('button',{name:'패키지 가져오기',exact:true}).click();
  await page.getByRole('dialog').getByPlaceholder('C:\\모델\\expert.pt 또는 https://…').fill('nonexistent-expert.pt');
  await page.getByRole('button',{name:'파일 구성 확인',exact:true}).click();
  await expect(page.getByRole('dialog').getByText('버튼 검사: library/inspect',{exact:true})).toBeVisible();
});
