// Original CEO UI -> one delegated CTO task -> real Hermes file read -> original job result.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('@playwright/test');
const origin='http://127.0.0.1:8766',id='p_hushmind3_project-zero_a46c93b0';
async function api(operation,payload={},get=false){
 const r=await fetch(origin+(get?'/api?'+new URLSearchParams({operation,payload:JSON.stringify(payload)}):'/api'),
  get?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operation,payload})});
 const value=await r.json();assert.ok(r.ok,JSON.stringify(value));return value;
}
async function main(){
 const resume=process.argv.includes('--resume');
 assert.ok(resume||process.argv.includes('--allow-local-model'),'실제 모델 검사는 --allow-local-model이 필요합니다. 일반 회귀는 verify_project_zero.py를 사용하세요.');
 let blockers;
 for(let attempt=0;attempt<20;attempt++){
  blockers=(await api('system/blockers')).items;
  if(!blockers.length||blockers.some(item=>item!=='실행 중인 외부 프로젝트 요청'))break;
  await new Promise(resolve=>setTimeout(resolve,500));
 }
 assert.deepEqual(blockers,[]);
 const browser=await chromium.launch({headless:true}),out=path.resolve('runtime/projects/manage/verification');fs.mkdirSync(out,{recursive:true});
 let page,ownedSession;
 try{
  page=await browser.newPage({viewport:{width:1440,height:960}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(origin+'/assets/projects/'+id+'/index.html',{waitUntil:'networkidle'});
  const frame=page;await frame.locator('#message').waitFor({state:'visible'});
  const state=()=>frame.locator('body').evaluate(async()=>{
   const session=await fetch('/api/local/session').then(r=>r.json());
   const r=await fetch('/api/admin/ceo',{headers:{'X-Project-Zero-Token':session.token}});
   if(!r.ok)throw Error('Original app state HTTP '+r.status);return r.json();
  });
  const prior=await state(),ids=new Set(prior.delegated_jobs.map(j=>j.id));
  const resumeTask=resume?prior.delegated_jobs.find(j=>j.role==='CTO'&&j.type==='agent_task'&&/README/i.test(j.title)):null;
  if(resume)assert.ok(resumeTask,'No completed README verification task to resume');
  const message='CTO에게 README.md 파일을 실제로 읽어 앱의 목적과 현재 구현 범위를 확인하는 agent_task 업무 하나만 배정해줘. 읽기와 보고만 수행해.';
  if(!resume){await frame.locator('#message').fill(message);await frame.locator('#send').click()}
  const deadline=Date.now()+480000;let task,harness;
  while(Date.now()<deadline){
   const snapshot=await state();const jobs=snapshot.delegated_jobs.filter(j=>resume?j.id===resumeTask.id:!ids.has(j.id));
   if(jobs.length){assert.equal(jobs.length,1,'One explicit task only');task=jobs[0];assert.equal(task.role,'CTO');assert.equal(task.type,'agent_task')}
   harness=await api('projects/harness',{id},true);ownedSession=harness.session_id;
   if(task?.status==='failed')throw Error(task.error||task.result||'Delegated job failed');
   if(task&&['completed','done'].includes(task.status)&&harness.state==='complete')break;
   if(harness.state==='failed')throw Error(harness.error);
   await new Promise(resolve=>setTimeout(resolve,2000));
  }
  assert.ok(task,'Original CEO must create the delegated task');assert.ok(['completed','done'].includes(task.status),task.status);
  assert.equal(task.mode,'llm');assert.ok(/README|PROJECT ZERO|프로젝트제로/i.test(task.result));
  const tools=(harness.job.events||[]).filter(e=>e.name==='tool_start');assert.ok(tools.length,'Employee must use a real tool');
  assert.deepEqual(errors,[]);
  await frame.locator('button[data-view="tasks"]').first().click();await page.waitForTimeout(1000);
  await page.screenshot({path:path.join(out,'project-zero-cto.png')});
  const report={project:id,request:message,original_ui:true,task,session_id:ownedSession,tool_calls:tools,metrics:harness.job.metrics,
   js_errors:errors,limits:'One read-only README task; no business approval, production deployment, payments or source edits'};
  fs.writeFileSync(path.join(out,'project-zero-task.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify({task_id:task.id,status:task.status,mode:task.mode,result:task.result,tool_calls:tools.length,js_errors:errors}));
 }catch(error){
  if(page)await page.screenshot({path:path.join(out,'project-zero-task-failure.png')}).catch(()=>{});
  const current=await api('projects/harness',{id},true).catch(()=>null);
  if(ownedSession&&current?.session_id===ownedSession&&['running','waiting'].includes(current.state))await api('projects/harness',{id,action:'stop'});
  throw error;
 }finally{await browser.close()}
}
main().catch(e=>{console.error(e.message);process.exitCode=1});
