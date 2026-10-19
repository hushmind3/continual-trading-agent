// UI-only: real authenticated workspace, then explicitly simulated in-progress data. No model calls.
const {chromium}=require('@playwright/test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const origin='http://127.0.0.1:8766',id='p_hushmind3_project-zero_a46c93b0',out=path.resolve('runtime/projects/manage/verification');
async function api(operation,payload){const r=await fetch(origin+'/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operation,payload})});assert.ok(r.ok);return r.json()}
async function app(url,token=''){const r=await api('projects/invoke',{id,path:url,method:'GET',headers:token?{'X-Project-Zero-Token':token}:{}});assert.equal(r.status,200);return JSON.parse(Buffer.from(r.body,'base64').toString())}
async function main(){
 const token=(await app('/api/local/session')).token,state=await app('/api/admin/platform/workspace',token);
 const browser=await chromium.launch({headless:true});fs.mkdirSync(out,{recursive:true});let page;
 try{
  page=await browser.newPage({viewport:{width:1440,height:960}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(origin+'/#projects/app/'+id,{waitUntil:'networkidle'});await page.getByRole('textbox',{name:'CEO에게 보낼 메시지'}).waitFor();
  assert.equal(await page.locator('iframe').count(),0);await page.getByRole('textbox',{name:'CEO에게 보낼 메시지'}).fill('작성 중인 요청을 보존합니다');
  await page.getByRole('button',{name:'업무',exact:true}).click();await page.getByRole('heading',{name:'업무 현황',exact:true}).waitFor();await page.getByText('팀 역할과 담당 산출물',{exact:true}).click();await page.getByText(/요구사항·사용자 흐름·화면 구성/).waitFor();await page.screenshot({path:path.join(out,'project-zero-team-roles.png')});
  await page.getByRole('button',{name:'대화',exact:true}).click();assert.equal(await page.getByRole('textbox',{name:'CEO에게 보낼 메시지'}).inputValue(),'작성 중인 요청을 보존합니다');
  await page.screenshot({path:path.join(out,'project-zero-workspace-desktop.png')});
  let approvalClicks=0;const reportSummary='추천안: 로컬 홈페이지 제작\n이유: 고객 검증\n산출물: 홈페이지와 검사 결과\n승인 범위: 로컬 작업';const plan={report_message_id:'visual-report',meeting_id:'visual-plan',status:'pending',summary:reportSummary,tasks:[{phase:'requirements',role:'CPO',title:'요구사항 정리',brief:'정리',deliverable:'요구사항 문서',acceptance:'실제 문서 확인'}],jobs:[]};const simulated={...state,plans:[plan],ceo:{messages:[...state.ceo.messages,{id:'visual-report',seq:999999,speaker:'ceo',body:'[팀 회의 완료] '+reportSummary}]},meetings:[{id:'visual-only',status:'running',topic:'시각 검사 · 수익 가설 검토',summary:'',minutes:[{role:'CPO',name:'제품 책임자',statement:'**고객 문제**를 먼저 검증합니다.'},{role:'CTO',name:'기술 책임자',statement:'기술 가설과 구현 위험을 검토합니다.'}]}]};
  await page.route('**/api**',async route=>{const url=new URL(route.request().url());let operation=url.searchParams.get('operation'),payload={};if(route.request().method()==='POST'){const body=route.request().postDataJSON();operation=body.operation;payload=body.payload||{}}
   if(operation==='projects/invoke'&&payload.path==='/api/admin/platform/meeting-plans/visual-plan/decision'){approvalClicks++;plan.status='approved';return route.fulfill({json:{status:200,body:Buffer.from(JSON.stringify({status:'approved',jobs:[]})).toString('base64')}})}
   if(operation==='projects/invoke'&&payload.path==='/api/admin/platform/workspace')return route.fulfill({json:{status:200,body:Buffer.from(JSON.stringify(simulated)).toString('base64')}});
   if(operation==='projects/harness')return route.fulfill({json:{state:'running',phase:{kind:'meeting',role:'CMO',label:'회의 발언 작성',started_at:Date.now()/1000}}});
   return route.continue();
  });
  await page.reload({waitUntil:'networkidle'});await page.getByRole('button',{name:/^회의/}).first().click();
  await page.getByRole('region',{name:'회의 진행 상황'}).waitFor();assert.equal(await page.getByRole('region',{name:'회의 진행 상황'}).getByRole('listitem').count(),6);
  await page.getByText('발언 작성 중',{exact:true}).waitFor();await page.getByText('1. CPO · 제품 책임자',{exact:true}).click();assert.ok((await page.locator('strong').allTextContents()).includes('고객 문제'));
  await page.getByRole('button',{name:'새 회의',exact:true}).click();await page.getByRole('textbox',{name:'회의 주제'}).fill('');assert.equal(await page.getByRole('textbox',{name:'회의 주제'}).inputValue(),'');
  await page.screenshot({path:path.join(out,'project-zero-meeting-progress.png')});
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(300);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No horizontal overflow');
  await page.screenshot({path:path.join(out,'project-zero-workspace-mobile.png')});await page.getByRole('button',{name:'대화',exact:true}).click();const card=page.getByRole('region',{name:'회의 실행안 승인'});await card.waitFor();assert.equal(await card.locator('details[open]').count(),0);await card.getByRole('button',{name:'승인하고 실행',exact:true}).click();await card.getByText('승인됨',{exact:true}).waitFor();assert.equal(approvalClicks,1);await page.screenshot({path:path.join(out,'project-zero-execution-approval.png')});assert.deepEqual(errors,[]);
  const report={real_authenticated_workspace:true,role_personas_visible:true,draft_preserved:true,role_steps:6,partial_progress:'simulated CPO/CTO saved, CMO responding; no DB writes',viewports:[1440,390],horizontal_overflow:false,js_errors:errors,approval_click:'simulated endpoint; no DB jobs',model_calls:0};
  fs.writeFileSync(path.join(out,'project-zero-workspace.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }catch(error){if(page)await page.screenshot({path:path.join(out,'project-zero-workspace-failure.png')}).catch(()=>{});throw error}finally{await browser.close()}
}
main().catch(e=>{console.error(e.message);process.exitCode=1});
