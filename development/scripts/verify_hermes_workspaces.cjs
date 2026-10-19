// Original records + unified Hermes chat; submitted actions are intercepted, never sent to a model.
const {chromium}=require('@playwright/test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const origin='http://127.0.0.1:8766',out=path.resolve('runtime/ai_agent/Hermes/verification/workspace-tabs');
async function get(operation,payload={}){return (await fetch(origin+'/api?operation='+operation+'&payload='+encodeURIComponent(JSON.stringify(payload)))).json()}
async function main(){
 const tabs=(await get('projects/workspace-tabs')).items,connected=tabs.find(t=>t.conversation&&t.view==='talk');assert.ok(connected);
 const id=connected.id.split(':')[0],original=await get('projects/conversation',{id});assert.ok(original.messages.length);
 const browser=await chromium.launch({headless:true});fs.mkdirSync(out,{recursive:true});let page;
 try{
  page=await browser.newPage({viewport:{width:1440,height:960}});const errors=[],actions=[],forwarded=[];let injected=false,approved=false;
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api')){const b=r.postDataJSON();if(b?.operation?.endsWith('/chat')||b?.operation==='projects/invoke'&&b.payload?.path?.endsWith('/submit'))forwarded.push(b.operation)}});
  await page.route('**/api*',async route=>{const req=route.request(),url=new URL(req.url()),post=req.method()==='POST'?req.postDataJSON():null,op=post?.operation||url.searchParams.get('operation'),payload=post?.payload||JSON.parse(url.searchParams.get('payload')||'{}');
   if(op!=='projects/conversation')return route.continue();let result;
   if(req.method()==='POST'){actions.push(payload);if(payload.action==='send'){injected=true;result={accepted:true,request_id:'b'.repeat(32)}}else if(payload.action==='decision'){approved=true;result={status:'approved'}}else throw Error('Unexpected action')}
   else if(injected)result={messages:[...original.messages,{speaker:'owner',body:'통합 대화 전송 검사'},{speaker:'ceo',body:'**통합 답변 확인**\n\n[결과 문서](/assets/projects/verification/requirements.md)'}],ventures:approved?[]:[{id:'venture_ui_verification',name:'화면 검사 사업안',status:'pending',proposal_json:'{"name":"화면 검사 사업안","product":"로컬 검사"}'}],...(payload.request_id?{request:{status:'completed',error:''}}:{})};else return route.continue();
   await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(result)});
  });
  await page.goto(origin+'/#ai_agent/Hermes',{waitUntil:'networkidle'});
  const nav=page.getByRole('navigation',{name:'대화 작업 화면'});await nav.waitFor();assert.deepEqual(await nav.getByRole('button').allTextContents(),['대화','회사 현황','업무 실행 기록']);
  const composer=page.getByRole('textbox',{name:'헤르메스에게 보낼 메시지'});await page.getByText('AI 총괄 · 승인 후 실행',{exact:true}).waitFor();
  const owner=[...original.messages].reverse().find(m=>m.speaker==='owner');if(owner)assert.ok((await page.locator('.hermes-messages').textContent()).includes(owner.body));assert.equal(await page.locator('iframe:visible').count(),0);
  await composer.fill('통합 대화 초안 보존');await nav.getByRole('button',{name:'회사 현황',exact:true}).click();const frame=page.frameLocator('iframe[title="연결된 회사 운영 화면"]');await frame.locator('#overview.on').waitFor();await frame.getByRole('button',{name:'CEO와 이야기하기 →',exact:true}).click();await composer.waitFor();assert.equal(await composer.inputValue(),'통합 대화 초안 보존');assert.equal(await page.locator('iframe:visible').count(),0);
  await composer.fill('통합 대화 전송 검사');await page.getByRole('button',{name:'메시지 보내기',exact:true}).click();await page.locator('.hermes-messages strong').filter({hasText:'통합 답변 확인'}).waitFor();assert.equal(actions.filter(x=>x.action==='send').length,1);
  const approve=page.getByRole('button',{name:'승인 후 실행',exact:true}),read=page.getByRole('switch',{name:'읽기 모드',exact:true});if(await read.getAttribute('aria-checked')==='false')await read.click();assert.ok(await approve.isDisabled());await read.click();await approve.click();await approve.waitFor({state:'detached'});assert.equal(actions.filter(x=>x.action==='decision').length,1);assert.equal(actions.find(x=>x.action==='decision').approve,true);
  await page.getByRole('button',{name:'대화 기록 열기',exact:true}).click();const sidebar=page.getByRole('complementary',{name:'대화 기록'});assert.ok(await sidebar.getByRole('button',{name:/AI 총괄 · 회사 운영/,exact:true}).count());assert.ok(await sidebar.locator('.ha-session-choice').count()>1);await page.getByRole('button',{name:'대화 기록 닫기',exact:true}).click();
  await page.screenshot({path:path.join(out,'unified-chat.png')});await composer.fill('새로고침 뒤에도 남는 통합 초안');await page.reload({waitUntil:'networkidle'});await composer.waitFor();assert.equal(await composer.inputValue(),'새로고침 뒤에도 남는 통합 초안');
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(200);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,'unified-mobile.png')});
  await nav.getByRole('button',{name:'업무 실행 기록',exact:true}).click();await frame.locator('#results.on').waitFor();assert.ok(await frame.locator('html').evaluate(e=>e.scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]);assert.deepEqual(forwarded,[]);const report={unified_chat:true,original_history:true,tabs:3,approval:true,async_submit:true,draft_reload:true,normal_history_preserved:true,viewports:[1440,390],horizontal_overflow:false,js_errors:errors,model_submissions:0,mocked_actions:actions.length};fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }catch(e){if(page)await page.screenshot({path:path.join(out,'failure.png')});throw e}finally{await browser.close()}
}
main().catch(e=>{console.error(e.stack);process.exitCode=1});
