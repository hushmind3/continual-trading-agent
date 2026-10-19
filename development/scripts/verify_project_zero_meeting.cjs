// Explicit real-model verification: five specialist calls + CEO synthesis, without business approval.
const {chromium}=require('@playwright/test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const origin='http://127.0.0.1:8766',id='p_hushmind3_project-zero_a46c93b0',out=path.resolve('runtime/projects/manage/verification');
async function api(operation,payload={},get=false){const r=await fetch(origin+(get?'/api?'+new URLSearchParams({operation,payload:JSON.stringify(payload)}):'/api'),get?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operation,payload})});assert.ok(r.ok);return r.json()}
async function app(url,token=''){const r=await api('projects/invoke',{id,path:url,method:'GET',headers:token?{'X-Project-Zero-Token':token}:{}});assert.equal(r.status,200);return JSON.parse(Buffer.from(r.body,'base64').toString())}
async function main(){
 assert.ok(process.argv.includes('--allow-local-model'),'실제 모델 회의 검사는 --allow-local-model이 필요합니다.');
 const token=(await app('/api/local/session')).token,initial=await app('/api/admin/platform/workspace',token);
 assert.equal(initial.include_engine_context,false,'이 검사는 현재 주제 중심 맥락을 사용합니다.');
 assert.ok(!initial.meetings.some(m=>m.status==='running'),'An existing meeting must finish first');
 const before=await api('projects/harness',{id},true);assert.ok(!['running','waiting'].includes(before.state),'Do not overlap another app request');
 const browser=await chromium.launch({headless:true});fs.mkdirSync(out,{recursive:true});let page,meeting,last='';const stages=[],sessions=new Set();
 try{
  page=await browser.newPage({viewport:{width:1440,height:960}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(origin+'/#projects/app/'+id,{waitUntil:'networkidle'});await page.getByRole('button',{name:'회의',exact:true}).click();
  const topic='월 1,000만원 수익 목표의 사업 가설 검토. 실제 매출이 없다는 전제로 고객 검증·비용·기술 위험·품질의 반론을 제시하세요. 실행·구매·공개는 하지 않습니다.';
  if(!await page.getByRole('textbox',{name:'회의 주제'}).count())await page.getByRole('button',{name:'새 회의',exact:true}).click();
  await page.getByRole('textbox',{name:'회의 주제'}).fill(topic);await page.getByRole('button',{name:'회의 시작',exact:true}).click();
  const deadline=Date.now()+900000;
  while(Date.now()<deadline){
   const data=await app('/api/admin/platform/workspace',token),harness=await api('projects/harness',{id},true);meeting=data.meetings.find(m=>m.topic===topic&&!initial.meetings.some(old=>old.id===m.id));
   if(meeting){const stage=meeting.minutes.length+':'+(harness.phase?.role||'')+':'+meeting.status;if(stage!==last){last=stage;stages.push({saved:meeting.minutes.length,phase:harness.phase,status:meeting.status});console.log(JSON.stringify(stages.at(-1)))}
    if(harness.session_id)sessions.add(harness.session_id);
    if(meeting.status==='failed')throw Error(meeting.summary);if(meeting.status==='completed')break;
   }
   await new Promise(resolve=>setTimeout(resolve,2000));
  }
  assert.equal(meeting?.status,'completed');assert.deepEqual(meeting.minutes.map(m=>m.role),['CPO','CTO','CMO','CFO','QA']);assert.ok(meeting.summary);
  const after=await api('projects/harness',{id},true);assert.equal(after.request_number-before.request_number,6);assert.equal(sessions.size,6);
  await page.getByRole('heading',{name:'CEO · 회의 결론',exact:true}).waitFor({timeout:15000});assert.deepEqual(errors,[]);
  await page.screenshot({path:path.join(out,'project-zero-real-meeting.png')});
  const brandMentions=meeting.minutes.filter(m=>/DealPage/i.test(m.statement)).length+(/DealPage/i.test(meeting.summary)?1:0);
  const report={meeting,context:'focused business review',unselected_example_mentions:brandMentions,previous_meeting_id:initial.meetings[0]?.id,provider_calls:6,distinct_sessions:[...sessions],progress:stages,js_errors:errors,limits:'Real model role discussion only; no market research, revenue, product publication or business approval'};
  fs.writeFileSync(path.join(out,'project-zero-real-meeting.json'),JSON.stringify(report,null,2));assert.equal(brandMentions,0,'Unselected bundled product must not anchor this meeting');console.log(JSON.stringify({meeting_id:meeting.id,status:meeting.status,minutes:meeting.minutes.length,provider_calls:6,sessions:sessions.size,js_errors:errors}));
 }catch(error){if(page)await page.screenshot({path:path.join(out,'project-zero-real-meeting-failure.png')}).catch(()=>{});throw error}finally{await browser.close()}
}
main().catch(e=>{console.error(e.message);process.exitCode=1});
