const {chromium}=require('@playwright/test');
const fs=require('node:fs/promises');const path=require('node:path');
const root=path.resolve(__dirname,'../..');const base=path.join(root,'runtime/projects/manage/verification');
const id='p_hwkim3330_pluto-re_de08da1f';
async function api(operation,payload={}){const response=await fetch('http://127.0.0.1:8766/api',{method:'POST',signal:AbortSignal.timeout(20000),headers:{'content-type':'application/json'},body:JSON.stringify({operation,payload})});const value=await response.json();if(!response.ok)throw new Error(JSON.stringify(value));return value;}
async function until(callback,seconds=240){const end=Date.now()+seconds*1000;while(Date.now()<end){try{const value=await callback();if(value)return value}catch(e){if(e.fatal)throw e}await new Promise(resolve=>setTimeout(resolve,750))}throw new Error('verification wait timeout')}
(async()=>{
 await fs.mkdir(base,{recursive:true});
 const existing=await api('projects/detail',{id});
 if(existing.adapter?.kind!=='powershell'||existing.stage!=='ready')await api('projects/retry',{id,allow_agent:false});
 const record=await until(async()=>{const value=(await api('projects/installed')).items.find(item=>item.id===id);if(['failed','not_app','needs_adapter'].includes(value?.stage))throw Object.assign(new Error(value.error),{fatal:true});return value?.stage==='ready'?value:null});
 if(record.adapter.kind!=='powershell'||record.verification.entry_executed)throw new Error('incorrect runtime/verification classification');
 console.log('Original Windows installer recognized; no model used');
 const browser=await chromium.launch({headless:true});
 const target=path.join(base,'missing-game-for-installer');await fs.mkdir(target,{recursive:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:900}});const errors=[];
  await page.addInitScript(()=>localStorage.setItem('projects.korean','false'));
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8766/#'+record.menu);
  await page.getByText('Windows 프로그램 설치',{exact:true}).waitFor();
  await page.getByText('프로젝트 관리 · 앱 전용 폴더',{exact:true}).waitFor();
  await page.getByText(record.project_folder,{exact:true}).waitFor();
  await page.getByRole('button',{name:'폴더 선택',exact:true}).waitFor();
  await page.getByLabel('StarCraft 폴더',{exact:true}).fill(target);
  const [started]=await Promise.all([page.waitForResponse(response=>response.url().endsWith('/api')&&JSON.parse(response.request().postData()||'{}').operation==='projects/setup'),page.getByRole('button',{name:'원본 프로그램 설치',exact:true}).click()]);
  if(!started.ok())throw new Error(await started.text());
  const result=await until(async()=>{const value=await api('projects/setup/status',{id});return ['complete','failed','interrupted'].includes(value.state)?value:null},45);
  if(result.state!=='failed'||!result.log.includes('StarCraft.exe not found'))throw new Error(JSON.stringify(result));
  await page.getByLabel('설치 실행 결과').filter({hasText:'StarCraft.exe not found'}).waitFor();
  console.log('Original prerequisite check executed; failed before downloads as expected');
  const source=record.active_source;
  await fs.rename(path.join(source,'../setup.log'),path.join(base,'windows-installer-prerequisite.log'));
  await fs.rename(path.join(source,'../setup-state.json'),path.join(base,'windows-installer-prerequisite.json'));
  await page.reload();await page.getByText('Windows 프로그램 설치',{exact:true}).waitFor();
  await page.getByRole('button',{name:'원본 프로그램 설치',exact:true}).waitFor();
  await page.getByText('서버 연결',{exact:true}).waitFor();
  await page.screenshot({path:path.join(base,'windows-installer-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('horizontal overflow');
  await page.screenshot({path:path.join(base,'windows-installer-mobile.png'),fullPage:true});
  if(errors.length)throw new Error(JSON.stringify(errors));
  const report={original_script_detected:true,typed_controls:true,managed_project_folder:true,folder_button_visible:true,native_folder_dialog_tested:false,required_folder:true,original_prerequisite_check:true,downloads_started:false,game_installed:false,mobile_overflow:false,javascript_errors:errors,model_used:false};
  await fs.writeFile(path.join(base,'windows-installer-ui.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close();await fs.rmdir(target).catch(()=>{});await fs.rmdir(path.join(record.active_source,'../setup-cache')).catch(()=>{});}
})().catch(e=>{console.error(e);process.exitCode=1});
