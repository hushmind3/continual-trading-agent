// One live UI flow: export -> file install -> original UI -> uninstall. No LLM calls.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const {chromium}=require('@playwright/test');
const root=path.resolve(__dirname,'../..'),base='http://127.0.0.1:8766';
const output=path.join(root,'runtime/projects/manage/verification');
const repository='platform-verification/portable-check';
const imported='p_'+repository.replace(/[^a-z0-9_-]/g,'_')+'_'+crypto.createHash('sha256').update(repository).digest('hex').slice(0,8);
async function api(operation,payload={}){
 for(let attempt=0;;attempt++){
  try{
   const response=await fetch(base+'/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operation,payload})});
   const data=await response.json();if(!response.ok)throw Error(data.detail||response.status);return data;
  }catch(error){
   if(operation!=='projects/installed'||attempt>=20)throw error;
   await new Promise(resolve=>setTimeout(resolve,500));
  }
 }
}
async function main(){
 fs.mkdirSync(output,{recursive:true});
 const existing=await api('projects/installed');
 if(existing.items.some(item=>['p_portable_verify',imported].includes(item.id)))throw Error('Previous verification app exists. Refusing to overwrite.');
 const bootstrap=spawnSync(path.join(root,'.venv/Scripts/python.exe'),['-I','-B','-c',
  'import sys,json;from pathlib import Path;sys.path.insert(0,"backend");from platform_modules import mount_namespaces;mount_namespaces();from platform_plugins.projects.store import STATE,save;source=STATE/"projects/p_portable_verify/versions/v1/source";source.mkdir(parents=True);(source/"index.html").write_text("<!doctype html><html><head><title>Portable app</title></head><body><h1>Portable app works</h1></body></html>",encoding="utf8");save({"id":"p_portable_verify","repository":"'+repository+'","url":"https://github.com/'+repository+'","title":"Portable verification app","stage":"ready","detail":"Verification fixture","active_source":str(source),"adapter":{"kind":"static","directory":".","output":"."}})'],{cwd:root,encoding:'utf8'});
 if(bootstrap.status)throw Error(bootstrap.stderr);
 const browser=await chromium.launch({headless:true});let page;
 const errors=[],report={};
 try{
  page=await browser.newPage({viewport:{width:1440,height:900}});
  await page.addInitScript(()=>localStorage.setItem('projects.korean','false'));
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(base+'/?screen=projects#projects/manage/installed');
  const row=page.locator('article').filter({hasText:'Portable verification app'});
  const downloadEvent=page.waitForEvent('download');
  await row.getByRole('button',{name:'내보내기',exact:true}).click();
  const download=await downloadEvent;const zip=path.join(output,'portable-ui.zip');await download.saveAs(zip);
  report.download=download.suggestedFilename();
  console.log('UI: app ZIP downloaded');
  if(!report.download.endsWith('.zip'))throw Error('ZIP download failed');
  await page.goto(base+'/?screen=projects#projects/manage/search');
  if(await page.getByRole('checkbox',{name:'미지원 구조를 모델로 자동 변환',exact:true}).isChecked())throw Error('Model conversion must default off');
  const importedEvent=page.waitForResponse(response=>response.url()===base+'/api'&&response.request().method()==='POST'&&response.request().postDataJSON()?.operation==='projects/import');
  await page.getByLabel('앱 패키지 파일').setInputFiles(zip);
  const response=await importedEvent;if(!response.ok())throw Error(await response.text());
  const deadline=Date.now()+100000;
  while(true){
   const data=await api('projects/installed'),project=data.items.find(item=>item.id===imported);
   if(project?.stage==='ready'){report.installed=project.stage;report.menu=project.menu;break}
   if(project&&['failed','needs_adapter','cancelled'].includes(project.stage))throw Error(project.error||project.stage);
   if(Date.now()>deadline)throw Error('Automatic installation did not reach ready');
   await new Promise(resolve=>setTimeout(resolve,1000));
  }
  await page.waitForURL(url=>url.hash==='#'+report.menu,{timeout:30000});
  const frame=page.frameLocator('iframe');await frame.getByRole('heading',{name:'Portable app works'}).waitFor();
  report.original_ui=true;await page.screenshot({path:path.join(output,'portable-app.png')});
  console.log('UI: file installed, menu activated, original app rendered');
  await page.goto(base+'/?screen=projects#projects/manage/installed');
  const app=page.locator('article').filter({hasText:'portable-check'}).filter({hasNotText:'Portable verification app'});
  await app.getByRole('button',{name:'제거',exact:true}).click();
  await app.waitFor({state:'detached'});
  await page.waitForFunction(()=>!sessionStorage.getItem('projects.pending-removal'),undefined,{timeout:45000});
  await page.getByText('portable-check',{exact:true}).waitFor({state:'detached',timeout:45000});
  report.menu_removed=true;
  const source=path.join(root,'runtime/projects/manage/projects',imported);
  if(fs.existsSync(source)||fs.existsSync(path.join(root,'modules','external_'+imported)))throw Error('Uninstall left app files behind');
  report.uninstalled=true;report.javascript_errors=errors;
  if(errors.length)throw Error(errors.join('\n'));
 }finally{
  await browser.close();
  for(const id of [imported,'p_portable_verify']){
   const list=await api('projects/installed');if(!list.items.some(item=>item.id===id))continue;
   try{await api('projects/cancel',{id})}catch{}
   const deadline=Date.now()+15000;
   while(true){try{await api('projects/remove',{id});break}catch(error){if(Date.now()>deadline)throw error;await new Promise(resolve=>setTimeout(resolve,500))}}
  }
  fs.writeFileSync(path.join(output,'portable-ui.json'),JSON.stringify(report,null,2));
 }
 console.log(JSON.stringify(report));
}
main().catch(error=>{console.error(error);process.exitCode=1});
