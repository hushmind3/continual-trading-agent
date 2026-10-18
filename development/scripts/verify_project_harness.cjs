// One real owner-chat request: original UI -> provider hook -> Hermes tools -> original DB/UI.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {chromium}=require('@playwright/test');
const origin='http://127.0.0.1:8766',id='p_hushmind3_project-zero_a46c93b0';
async function api(operation,payload={}){
 const get=operation==='projects/harness'&&!payload.action;
 const r=await fetch(origin+(get?'/api?'+new URLSearchParams({operation,payload:JSON.stringify(payload)}):'/api'),
  get?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operation,payload})});
 const data=await r.json();if(!r.ok)throw Error(JSON.stringify(data));return data;
}
async function main(){
 const resume=process.argv.includes('--resume');
 assert.deepEqual((await api('system/blockers')).items,[]);
 const project=await api('projects/detail',{id});assert.ok(project.harness_available);
 if(!resume)await api('projects/settings',{id,use_harness:true});
 const out=path.resolve('runtime/projects/manage/verification');fs.mkdirSync(out,{recursive:true});
 const directory=path.join(project.active_source,'verification','harness-live'),file=path.join(directory,'probe.txt');
 assert.ok(resume?fs.existsSync(file):!fs.existsSync(directory),'Test folder ownership must match the run');
 const proof=resume?fs.readFileSync(file,'utf8'):'HERMES-'+crypto.randomBytes(10).toString('hex');
 assert.ok(proof.startsWith('HERMES-'));const hasProof=text=>text.replace(/\s+/g,'').includes(proof.replace(/\s+/g,''));
 let browser,page,success=false;
 try{
  if(!resume){fs.mkdirSync(directory,{recursive:true});fs.writeFileSync(file,proof,'utf8')}
  browser=await chromium.launch({headless:true});page=await browser.newPage({viewport:{width:1440,height:960}});const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(origin+'/#projects/app/'+id,{waitUntil:'networkidle'});
  await page.getByRole('button',{name:'Hermes 하네스',exact:true}).waitFor();
  const frame=page.frameLocator('iframe[title="project-zero 원본 화면"]');
  const saved=fs.readFileSync(path.join(project.active_source,'data/admin.token'),'utf8').trim();
  const source=fs.readFileSync(path.join(project.active_source,'server.py'),'utf8');
  const local=source.match(/['"]([^'"]+)['"]\s+if local_private_mode\(\)/)?.[1];
  const record=JSON.parse(fs.readFileSync(path.resolve('runtime/projects/manage/registry',id+'.json'),'utf8'));
  let token;
  for(const candidate of [record.environment?.PROJECT_ZERO_ADMIN_TOKEN,local,saved].filter(Boolean)){
   const check=await api('projects/invoke',{id,path:'/api/admin/team',method:'GET',headers:{'X-Project-Zero-Token':candidate}});
   if(check.status===200){token=candidate;break}
  }
  assert.ok(token,'Use the original server authentication policy');
  await frame.locator('#token').fill(token);
  await frame.locator('#loginForm button[type="submit"]').click();await frame.locator('#login').waitFor({state:'hidden',timeout:15000});
  const talkTab=frame.locator('button[data-tab="talk"]');if(await talkTab.count())await talkTab.first().click();
  const composer=frame.locator('#prompt,#message').first(),messages=frame.locator('#messages,#chat').first();
  const message='하네스 연결 확인 질문입니다. 실제 파일 읽기 도구로 다음 파일을 읽고 그 안의 확인 문자열만 그대로 답장하세요. 이것은 단순 질문입니다. 업무를 배정하거나 회의를 시작하지 마세요. 파일을 변경하지 마세요. tasks는 빈 배열이어야 합니다. 파일: '+file;
  if(!resume){await composer.fill(message);await frame.locator('#send').click()}
  const deadline=Date.now()+600000;let harness;
  while(Date.now()<deadline){
   harness=await api('projects/harness',{id});
   const body=await messages.innerText();
   if(hasProof(body)&&harness.state==='complete')break;
   if(harness.state==='failed')throw Error(harness.error);
   await new Promise(resolve=>setTimeout(resolve,1500));
  }
  assert.equal(harness.state,'complete');
  assert.ok(hasProof(await messages.innerText()),'The original chat must display the unknown characters (whitespace ignored)');
  const events=harness.job?.events||[];
  assert.ok(events.some(event=>/tool/.test(event.name)),'Actual Hermes tool events must exist');
  await page.getByRole('button',{name:'Hermes 하네스',exact:true}).click();
  await page.getByRole('heading',{name:'Hermes · 작업 내역'}).waitFor();
  await page.screenshot({path:path.join(out,'project-zero-hermes-harness.png')});
  assert.deepEqual(errors,[]);
  const report={project:id,source:project.active_source,original_chat:true,unknown_file_read:true,proof_comparison:'whitespace ignored; model inserted spaces',session_id:harness.session_id,
   engine_state:harness.job.state,event_count:events.length,events,metrics:harness.job.metrics,js_errors:errors,model_test:'one real chat request; no business job requested'};
  fs.writeFileSync(path.join(out,'project-harness.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify({original_chat:true,unknown_file_read:true,session_id:harness.session_id,event_count:events.length,js_errors:errors}));success=true;
 }catch(error){
  if(page){await page.screenshot({path:path.join(out,'project-harness-failure.png')}).catch(()=>{});const login=await page.frameLocator('iframe').locator('#loginError').innerText().catch(()=>'');if(login)console.error('Login response:',login)}
  throw error;
 }finally{
  if(!success)await api('projects/harness',{id,action:'stop'}).catch(()=>{});
  if(browser)await browser.close();
  if(fs.existsSync(file))fs.unlinkSync(file);
  if(fs.existsSync(directory))fs.rmdirSync(directory);
  const parent=path.dirname(directory);if(fs.existsSync(parent)&&fs.readdirSync(parent).length===0)fs.rmdirSync(parent);
 }
}
main().catch(e=>{console.error(e.message);process.exitCode=1});
