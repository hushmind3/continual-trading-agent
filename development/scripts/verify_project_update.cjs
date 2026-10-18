// Real GitHub update, original authenticated UI, and unchanged platform process.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process'),{chromium}=require('@playwright/test');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'runtime/projects/manage/verification');
const origin='http://127.0.0.1:8766',id='p_hushmind3_project-zero_a46c93b0';
async function api(operation,payload={}){
 const response=await fetch(origin+'/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operation,payload})});
 const data=await response.json();if(!response.ok)throw Error(JSON.stringify(data));return data;
}
async function main(){
 fs.mkdirSync(out,{recursive:true});assert.deepEqual((await api('system/blockers')).items,[]);
 const before=await api('health'),old=await api('projects/detail',{id});
 const previousTokenFile=path.join(old.active_source,'data/admin.token');
 const previousToken=fs.existsSync(previousTokenFile)?fs.readFileSync(previousTokenFile,'utf8'):null;
 await api('projects/install',{url:'https://github.com/hushmind3/project-zero.git',allow_agent:false});
 let installed;const deadline=Date.now()+900000;
 while(Date.now()<deadline){
  installed=await api('projects/detail',{id});
  if(installed.stage==='ready')break;
  if(['failed','cancelled','needs_adapter','not_app'].includes(installed.stage))throw Error(installed.error||installed.detail);
  await new Promise(resolve=>setTimeout(resolve,1500));
 }
 assert.equal(installed.stage,'ready');assert.equal(installed.adapter.app,'server:app');assert.equal(installed.adapter.ui.kind,'asgi');
 assert.equal(path.basename(installed.project_folder),'project-zero');
 assert.match(path.basename(path.dirname(installed.active_source)),/^version-\d+$/);
 const remote=execFileSync('git',['ls-remote','https://github.com/hushmind3/project-zero.git','HEAD'],{encoding:'utf8'}).split(/\s/)[0];
 assert.equal(installed.source_commit,remote);
 const after=await api('health');assert.equal(after.pid,before.pid,'An app update must not restart the platform');
 const health=await api('projects/invoke',{id,path:'/healthz',method:'GET'});assert.equal(health.status,200);
 const denied=await api('projects/invoke',{id,path:'/api/admin/team',method:'GET'});assert.equal(denied.status,401);
 const browser=await chromium.launch({headless:true}),errors=[];
 try{
  const page=await browser.newPage({viewport:{width:1440,height:960}});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(origin+'/#projects/app/'+id,{waitUntil:'networkidle'});
  const frame=page.frameLocator('iframe[title="project-zero 원본 화면"]');
  await frame.getByRole('button',{name:'경영실 입장'}).waitFor();
  const token=fs.readFileSync(path.join(installed.active_source,'data/admin.token'),'utf8').trim();
  if(previousToken!==null)assert.ok(token===previousToken.trim(),'An update must preserve owner credentials');
  await frame.getByPlaceholder('관리자 접속 코드').fill(token);await frame.getByRole('button',{name:'경영실 입장'}).click();
  await frame.locator('#teamGrid .team-card').first().waitFor({timeout:30000});
  await page.screenshot({path:path.join(out,'project-zero-current-ui.png')});
  assert.equal(await frame.locator('body').evaluate(el=>el.scrollWidth>innerWidth+1),false);
  assert.deepEqual(errors,[]);
  const result={repository:installed.repository,source_commit:remote,adapter:installed.adapter,folder:installed.project_folder,
   prior_revision:old.install_revision,revision:installed.install_revision,platform_pid_before:before.pid,platform_pid_after:after.pid,
   real_health_status:health.status,unauthorized_status:denied.status,owner_credential_preserved:previousToken!==null,authenticated_dashboard:true,js_errors:errors};
  fs.writeFileSync(path.join(out,'project-update.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
}
main().catch(e=>{console.error(e.message);process.exitCode=1});
