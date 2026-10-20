// Verify native CEO transport and retained original UI; every model write is intercepted.
const {chromium}=require('@playwright/test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const origin='http://127.0.0.1:8766',out=path.resolve('runtime/ai_agent/Hermes/verification/workspace-tabs');
async function get(operation,payload={}){return (await fetch(origin+'/api?operation='+operation+'&payload='+encodeURIComponent(JSON.stringify(payload)))).json()}
async function main(){
 const tabs=(await get('projects/workspace-tabs')).items,connected=tabs.find(t=>t.conversation&&t.view==='talk');assert.ok(connected?.session_id);
 const id=connected.id.split(':')[0],sid=connected.session_id,settings=await get('ai_agent/Hermes/settings');
 const browser=await chromium.launch({headless:true});fs.mkdirSync(out,{recursive:true});let page;
 try{
  page=await browser.newPage({viewport:{width:1440,height:960}});const errors=[],submitted=[],actions=[];let approved=false,confirmAllowed=false;
  page.on('dialog',dialog=>confirmAllowed?dialog.accept():dialog.dismiss());
  const messages=[{role:'user',content:'이전 회사 대화'},{role:'assistant',content:'이전 총괄 답변'}];
  const metric={generation_tps:42.5,input_tokens:3210,output_tokens:84,api_calls:1,context_tokens:3800,context_limit:65536,elapsed_seconds:12};
  let status={job:{state:'idle',session_id:null,events:[],error:'',metrics:{}},local_model:{running:true,state:'ready'}};
  const fulfill=(route,result)=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(result)});
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api*',async route=>{
   const req=route.request(),url=new URL(req.url()),post=req.method()==='POST'?req.postDataJSON():null,op=post?.operation||url.searchParams.get('operation'),payload=post?.payload||JSON.parse(url.searchParams.get('payload')||'{}');
   if(op==='ai_agent/Hermes/status')return fulfill(route,status);
   if(op==='ai_agent/Hermes/settings'||op==='ai_agent/Hermes/settings/save')return fulfill(route,settings);
   if(op==='ai_agent/Hermes/sessions')return fulfill(route,[{id:'ordinary_fixture',title:'기존 일반 대화'},{id:sid,title:'AI 총괄'}]);
   if(op==='ai_agent/Hermes/session')return fulfill(route,{session:{id:payload.id,title:payload.id===sid?'AI 총괄':'기존 일반 대화'},messages:payload.id===sid?messages:[{role:'user',content:'기존 일반 대화 보존'}]});
   if(op==='ai_agent/Hermes/autonomy')return fulfill(route,{});
   if(op==='ai_agent/Hermes/chat'){
    submitted.push(payload);assert.equal(payload.session_id,sid);assert.ok(['chat','goal','loop'].includes(payload.mode));
    messages.push({role:'user',content:payload.message},{role:'assistant',content:'**네이티브 총괄 답변 확인**'});
    status={...status,job:{state:'complete',session_id:sid,events:[],error:'',text:'네이티브 총괄 답변 확인',metrics:metric}};return fulfill(route,status);
   }
   if(op==='projects/conversation'){
    if(post){actions.push(payload);if(payload.action==='session')return fulfill(route,{session_id:sid});if(payload.action==='decision'){approved=payload.approve;return fulfill(route,{session_id:sid,name:'화면 검사 사업안'})}throw Error('Legacy company submission: '+payload.action)}
    return fulfill(route,{session_id:sid,ventures:approved?[]:[{id:'venture_ui_fixture',name:'화면 검사 사업안',status:'pending',proposal_json:'{"goal":"로컬 검사"}'}],progress:{approved:1,published:false,payment_connected:false,usage:{requests:0}}});
   }
   if(post&&!['projects/invoke','state'].includes(op))throw Error('Unexpected unmocked mutation: '+op);
   return route.continue();
  });
  await page.goto(origin+'/#ai_agent/Hermes',{waitUntil:'networkidle'});
  const nav=page.getByRole('navigation',{name:'대화 작업 화면'});await nav.waitFor();assert.deepEqual(await nav.getByRole('button').allTextContents(),['대화','회사 현황','업무 실행 기록']);
  const mode=page.getByRole('combobox',{name:'실행 방식',exact:true}),composer=page.getByRole('textbox',{name:'헤르메스에게 보낼 메시지'});
  await mode.selectOption('company');await page.locator('.hermes-messages').getByText('이전 회사 대화',{exact:true}).waitFor();assert.equal(await mode.inputValue(),'chat');
  await composer.fill('네이티브 총괄 전송 검사');await mode.selectOption('goal');assert.equal(await composer.inputValue(),'네이티브 총괄 전송 검사');await page.getByRole('button',{name:'메시지 보내기',exact:true}).click();await page.locator('.hermes-messages strong').getByText('네이티브 총괄 답변 확인',{exact:true}).waitFor();
  assert.equal(submitted[0].mode,'goal');assert.equal(submitted[0].session_id,sid);await page.getByText('42.5 tok/s',{exact:true}).waitFor();
  await mode.selectOption('loop');assert.equal(await mode.inputValue(),'loop');await mode.selectOption('chat');
  const business=page.getByRole('complementary',{name:'사업 관리',exact:true});if(!await business.isVisible())await page.getByRole('button',{name:'사업 관리 보기',exact:true}).click();await business.getByText('로컬 제작 승인됨',{exact:true}).waitFor();
  const approve=page.getByRole('button',{name:'사업 승인',exact:true}),read=page.getByRole('switch',{name:'읽기 모드',exact:true});if(await read.getAttribute('aria-checked')==='false')await read.click();assert.ok(await approve.isDisabled());await read.click();await approve.click();assert.equal(actions.filter(a=>a.action==='decision').length,0);confirmAllowed=true;await approve.click();await approve.waitFor({state:'detached'});for(let i=0;i<60&&submitted.length<2;i++)await page.waitForTimeout(50);assert.equal(submitted.length,2);assert.equal(submitted[1].mode,'goal');assert.equal(actions.filter(a=>a.action==='decision').length,1);
  await composer.fill('새로고침 보존 초안');await page.reload({waitUntil:'networkidle'});await composer.waitFor();assert.equal(await composer.inputValue(),'새로고침 보존 초안');
  await nav.getByRole('button',{name:'회사 현황',exact:true}).click();const frame=page.frameLocator('iframe[title="연결된 회사 운영 화면"]');await frame.locator('#overview.on').waitFor();await frame.locator('#teamGrid .team-card').first().waitFor();assert.ok((await frame.locator('#teamGrid').innerText()).includes('누적 완료'));
  await frame.locator('#overview [data-tab="talk"]').first().click();await page.waitForFunction(()=>document.querySelector('nav[aria-label="대화 작업 화면"] button[aria-current="page"]')?.textContent==='대화');
  await page.screenshot({path:path.join(out,'native-unified-chat.png')});
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(250);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  const close=page.getByRole('button',{name:'사업 관리 닫기',exact:true});if(await close.isVisible())await close.click();await page.getByRole('button',{name:'사업 관리 보기',exact:true}).click();await business.waitFor();await close.click();await page.screenshot({path:path.join(out,'native-unified-mobile.png')});
  await nav.getByRole('button',{name:'업무 실행 기록',exact:true}).click();await frame.locator('#results.on').waitFor();assert.ok(await frame.locator('html').evaluate(e=>e.scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]);assert.ok(!actions.some(a=>a.action==='send'));const report={native_company_session:true,same_session_goal_loop:true,native_metrics:true,original_company_ui:true,business_approval:true,draft_reload:true,viewports:[1440,390],js_errors:errors,horizontal_overflow:false,mocked_model_calls:submitted.length,real_model_calls:0};fs.writeFileSync(path.join(out,'native-ui-result.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }catch(e){if(page)await page.screenshot({path:path.join(out,'native-ui-failure.png')});throw e}finally{await browser.close()}
}
main().catch(e=>{console.error(e.stack);process.exitCode=1});
