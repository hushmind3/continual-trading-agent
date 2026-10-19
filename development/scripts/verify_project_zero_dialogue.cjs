// Actual CEO reply checks only; never approve plans or delegate implementation.
const {strict:assert}=require('node:assert'),fs=require('node:fs');
const id='p_hushmind3_project-zero_a46c93b0',base='http://127.0.0.1:8766';
async function app(path,token='',body){const r=await fetch(base+'/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operation:'projects/invoke',payload:{id,path,method:body?'POST':'GET',headers:{'content-type':'application/json','X-Project-Zero-Token':token},body:body?JSON.stringify(body):''}})});const v=await r.json();assert.ok(v.status>=200&&v.status<300,'App HTTP '+v.status);return JSON.parse(Buffer.from(v.body,'base64').toString())}
async function main(){
 assert.ok(process.argv.includes('--allow-local-model'),'Requires --allow-local-model');
 const token=(await app('/api/local/session')).token,reports=[];
 const cases=[{name:'role reference',message:'설계는 누가 담당해? CPO와 CTO, QA가 각각 뭘 맡는지 설명해 줘. 지금은 설명만 하고 실행하지 마.',roles:true},
 {name:'ordinary discussion',message:'여행 계획용 홈페이지 아이디어 두 가지만 대화로 얘기해 줘. 아직 초안은 만들지 말고 실행도 하지 마.'}];
 for(const sample of cases){
  const before=await app('/api/admin/platform/workspace',token);
  assert.ok(!before.meetings.some(m=>m.status==='running')&&!before.requests.some(r=>r.status==='working')&&!before.plan_preparing.length,'Existing user work must finish first');
  assert.equal(before.include_engine_context,false,'Focused app context expected');
  const known=new Set(before.ceo.messages.map(m=>m.id)),jobs=new Set(before.jobs.map(j=>j.id)),meetings=new Set(before.meetings.map(m=>m.id));
  const submitted=await app('/api/admin/ceo/chat/submit',token,{message:sample.message});console.log(JSON.stringify({case:sample.name,request_id:submitted.request_id}));
  let result;const deadline=Date.now()+300000;
  while(Date.now()<deadline){await new Promise(r=>setTimeout(r,3000));const state=await app('/api/admin/platform/workspace',token),request=state.requests.find(r=>r.id===submitted.request_id);if(request&&request.status!=='working'){
   const reply=state.ceo.messages.filter(m=>m.speaker==='ceo'&&!known.has(m.id)).at(-1)?.body||'';
   result={case:sample.name,request_id:submitted.request_id,actual_model:true,reply,elapsed_seconds:request.elapsed_seconds,error:request.error,
    new_jobs:state.jobs.filter(j=>!jobs.has(j.id)).length,new_meetings:state.meetings.filter(m=>!meetings.has(m.id)).length,
    unrequested_examples:(reply.match(/deal\s*page|딜페이지/ig)||[]).length,unrelated_host_projects:(reply.match(/금융\s*매매|매매\s*모델/ig)||[]).length,
    stale_business_claims:sample.roles?(reply.match(/매출\s*0|거래처\s*0|고객\s*0/g)||[]).length:0};
   reports.push(result);fs.writeFileSync('runtime/projects/manage/verification/project-zero-dialogue-live.json',JSON.stringify({reports},null,2));console.log(JSON.stringify(result));
   assert.equal(result.error,'');assert.ok(reply);assert.equal(result.new_jobs,0);assert.equal(result.new_meetings,0);assert.equal(result.unrequested_examples,0);assert.equal(result.unrelated_host_projects,0);assert.equal(result.stale_business_claims,0);
   if(sample.roles)for(const role of ['CPO','CTO','QA'])assert.ok(reply.includes(role),'Missing '+role);
   break;
  }}
  assert.ok(result,'Still generating; not cancelled');
 }
}
main().catch(e=>{console.error(e.message);process.exitCode=1});
