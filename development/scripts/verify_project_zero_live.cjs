// Replay the user's greeting through the original UI. No probe file, business creation or approval.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('@playwright/test');
const origin='http://127.0.0.1:8766',id='p_hushmind3_project-zero_a46c93b0';
async function api(operation,payload={},get=false){
 const response=await fetch(origin+(get?'/api?'+new URLSearchParams({operation,payload:JSON.stringify(payload)}):'/api'),
  get?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operation,payload})});
 const data=await response.json();assert.ok(response.ok,JSON.stringify(data));return data;
}
async function main(){
 const resume=process.argv.includes('--resume');
 assert.ok(resume||process.argv.includes('--allow-local-model'),'실제 모델 검사는 --allow-local-model이 필요합니다. 일반 회귀는 verify_project_zero.py를 사용하세요.');
 assert.deepEqual((await api('system/blockers')).items,[]);
 const project=await api('projects/detail',{id});assert.equal(project.harness.enabled,true);
 const out=path.resolve('runtime/projects/manage/verification');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true});let page,ownedSession;
 try{
  page=await browser.newPage({viewport:{width:1440,height:960}});const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(origin+'/assets/projects/'+id+'/index.html',{waitUntil:'networkidle'});
  const frame=page;
  await frame.locator('#login').waitFor({state:'hidden',timeout:20000});
  await frame.locator('#message').waitFor({state:'visible',timeout:15000});
  const oldNumber=project.harness.request_number||0;
  const before=await frame.locator('#chat').innerText();
  if(!resume){await frame.locator('#message').fill('안녕');await frame.locator('#send').click()}
  const deadline=Date.now()+240000;let harness;
  while(Date.now()<deadline){
   harness=await api('projects/harness',{id},true);
   if(resume||harness.request_number>oldNumber){
    ownedSession=harness.session_id;
    if(harness.state==='complete')break;
    if(harness.state==='failed')throw Error(harness.error);
   }
   await new Promise(resolve=>setTimeout(resolve,1500));
  }
  if(!resume)assert.ok(harness.request_number>oldNumber,'Original UI must start a fresh model request');assert.equal(harness.state,'complete');
  const raw=harness.job.text.trim(),start=raw.indexOf('{'),end=raw.lastIndexOf('}');
  const answer=JSON.parse(raw.slice(start,end+1));const tasks=answer.tasks??[];assert.deepEqual(tasks,[]);
  assert.ok(/안녕|반갑|무엇|도와|어서|대표|주인|소유주/.test(answer.reply),'Expected a greeting response');
  assert.ok(!/probe\.txt|verification[/\\]|확인 문자열|파일을 찾|파일 확인/.test(answer.reply),'Do not resume historical file requests');
  const tools=(harness.job.events||[]).filter(event=>event.name==='tool_start');assert.equal(tools.length,0,'A greeting needs no tool execution');
  await page.waitForTimeout(2000);
  const after=await frame.locator('#chat').innerText();if(!resume)assert.notEqual(after,before);assert.ok(after.includes(answer.reply));
  assert.deepEqual(errors,[]);await page.screenshot({path:path.join(out,'project-zero-live.png')});
  const report={project:id,source:project.active_source,original_ui:true,local_auto_login:true,request:'안녕',reply:answer.reply,
   tasks,tool_calls:tools.length,session_id:harness.session_id,metrics:harness.job.metrics,js_errors:errors,
   limits:'One real greeting; business workflow separately tested with isolated DB and mocked models'};
  fs.writeFileSync(path.join(out,'project-zero-live.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }catch(error){
  if(page)await page.screenshot({path:path.join(out,'project-zero-live-failure.png')}).catch(()=>{});
  const current=await api('projects/harness',{id},true).catch(()=>null);
  if(ownedSession&&current?.session_id===ownedSession&&['running','waiting'].includes(current.state))await api('projects/harness',{id,action:'stop'});
  throw error;
 }finally{await browser.close()}
}
main().catch(error=>{console.error(error.message);process.exitCode=1});
