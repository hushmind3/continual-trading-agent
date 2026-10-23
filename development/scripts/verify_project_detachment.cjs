// Actual GitHub static-app install, UI, automatic separation and reconnection.
const {chromium}=require('@playwright/test');
const fs=require('node:fs/promises');
const path=require('node:path');
const {spawn}=require('node:child_process');
const net=require('node:net');
const root=path.resolve(__dirname,'../..');
const base=path.join(root,'runtime/projects/manage/verification');
const repository='https://github.com/mdn/beginner-html-site-styled';
async function api(operation,payload={}){
 const response=await fetch('http://127.0.0.1:8766/api',{method:'POST',signal:AbortSignal.timeout(10000),headers:{'content-type':'application/json'},body:JSON.stringify({operation,payload})});
 const value=await response.json();if(!response.ok)throw new Error(JSON.stringify(value));return value;
}
async function until(callback,seconds=180){const end=Date.now()+seconds*1000;while(Date.now()<end){try{const result=await callback();if(result)return result}catch(error){if(error.fatal)throw error}await new Promise(resolve=>setTimeout(resolve,500))}throw new Error('검사 대기 시간 초과')}
async function port(){return new Promise(resolve=>{const server=net.createServer();server.listen(0,'127.0.0.1',()=>{const value=server.address().port;server.close(()=>resolve(value))})})}
(async()=>{
 await fs.mkdir(base,{recursive:true});
 const browser=await chromium.launch({headless:true});let key;let process_;let removed=false;
 try{
  const page=await browser.newPage({viewport:{width:1440,height:900}});const errors=[];
  await page.addInitScript(()=>localStorage.setItem('projects.korean','false'));
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('http://127.0.0.1:8766/#projects/manage/search');
  await page.getByLabel('GitHub 저장소 주소').fill(repository);
  const [response]=await Promise.all([page.waitForResponse(response=>response.url().endsWith('/api')&&response.request().postData()?.includes('projects/install')),
    page.getByRole('button',{name:'설치',exact:true}).first().click()]);
  const initial=await response.json();key=initial.id;if(!key)throw new Error(JSON.stringify(initial));
  console.log('GitHub 다운로드·설치 요청 완료');
  const ready=await until(async()=>{const value=await api('projects/detail',{id:key});if(['failed','needs_adapter','not_app'].includes(value.stage))throw Object.assign(new Error(value.error),{fatal:true});return value.stage==='ready'?value:null});
  await page.goto('http://127.0.0.1:8766/#'+ready.menu);
  await page.locator('iframe').waitFor();
  await page.frameLocator('iframe').locator('h1').waitFor();
  console.log('원본 화면 표시 확인');
  await page.screenshot({path:path.join(base,'installed-github-app.png'),fullPage:true});
  await page.goto('http://127.0.0.1:8766/#projects/manage/installed');
  const card=page.locator('article').filter({has:page.getByRole('heading',{name:ready.title,exact:true})});
  await card.getByRole('button',{name:'설치 정보',exact:true}).click();
  if(await page.getByLabel('환경 설정 이름').isVisible())throw new Error('Optional environment settings must be collapsed');
  await page.keyboard.press('Escape');
  await card.getByRole('button',{name:'분리',exact:true}).click();
  const detached=await until(async()=>{const value=await api('projects/detail',{id:key});if(value.error)throw Object.assign(new Error(value.error),{fatal:true});return value.stage==='removed'?value:null});
  console.log('자동 분리 폴더 준비 완료');
  await until(async()=>!(await api('projects/installed')).active_module_ids.includes(ready.module_id));
  const independent=detached.standalone_path;const free=await port();
  const python=path.join(root,'.venv/platform/Scripts/python.exe');
  process_=spawn(python,['-I','-X','utf8',path.join(independent,'run.py'),'run','--port',String(free)],{cwd:independent,stdio:'ignore',windowsHide:true});
  await until(async()=>{const response=await fetch('http://127.0.0.1:'+free,{signal:AbortSignal.timeout(3000)});return response.ok},15);
  const independentPage=await browser.newPage();await independentPage.goto('http://127.0.0.1:'+free);await independentPage.locator('h1').waitFor();
  await independentPage.screenshot({path:path.join(base,'detached-github-app.png'),fullPage:true});await independentPage.close();
  console.log('분리 폴더 단독 실행 확인');
  process_.kill();await new Promise(resolve=>process_.once('exit',resolve));process_=null;
  await page.goto('http://127.0.0.1:8766/#projects/manage/installed');
  await card.getByRole('button',{name:'다시 연결',exact:true}).click();
  await until(async()=>{const row=(await api('projects/installed')).items.find(item=>item.id===key);return row?.stage==='ready'});
  console.log('다시 연결 확인');
  await api('projects/remove',{id:key});removed=true;
  await until(async()=>!(await api('projects/installed')).active_module_ids.includes(ready.module_id));
  await page.goto('http://127.0.0.1:8766/#projects/manage/installed');await page.getByRole('button',{name:'잔재 정리',exact:true}).waitFor();
  await page.setViewportSize({width:390,height:844});
  await page.getByText('서버 연결',{exact:true}).waitFor({timeout:30000});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('mobile horizontal overflow');
  await page.screenshot({path:path.join(base,'projects-mobile.png'),fullPage:true});
  if(errors.length)throw new Error(JSON.stringify(errors));
  const report={github_download:true,original_ui:true,optional_api_settings:true,automatic_detach:true,independent_run:true,reconnected:true,removed:true,mobile_overflow:false,javascript_errors:errors};
  await fs.writeFile(path.join(base,'detachment-ui.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{
  if(process_)process_.kill();
  if(key&&!removed){try{await api('projects/remove',{id:key})}catch{}}
  await browser.close();
 }
})().catch(error=>{console.error(error);process.exitCode=1});
