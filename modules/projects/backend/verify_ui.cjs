// Exercise the original built UI through the same single-gateway bridge, without another HTTP server.
const fs=require('node:fs'),path=require('node:path'),readline=require('node:readline'),{spawn}=require('node:child_process');
const {chromium}=require('@playwright/test');
async function main(){
 const cfg=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),origin='http://project.invalid',errors=[],prefix='/assets/projects/'+cfg.project_id+'/';
 let worker,reader;const pending=[];
 if(cfg.app){worker=spawn(cfg.python,['-I','-X','utf8','-B',path.join(__dirname,'app_worker.py'),cfg.app.folder,cfg.app.target,...(cfg.app.packages?[cfg.app.packages]:[])],{env:{...process.env,...cfg.environment,PYTHONUTF8:'1'},stdio:['pipe','pipe','inherit']});
  reader=readline.createInterface({input:worker.stdout});reader.on('line',line=>{try{const next=pending.shift();if(next)next.resolve(JSON.parse(line))}catch(e){errors.push(e.message)}});
  worker.on('exit',()=>{for(const job of pending.splice(0))job.reject(Error('앱 실행기가 종료됐습니다.'))});
 }
 const call=payload=>new Promise((resolve,reject)=>{if(!worker)return reject(Error('API 실행기가 없습니다.'));pending.push({resolve,reject});worker.stdin.write(JSON.stringify(payload)+'\n')});
 const browser=await chromium.launch({headless:true});
 try{const page=await browser.newPage();page.on('pageerror',e=>errors.push(e.message));
  page.on('requestfailed',r=>errors.push(r.url()+': '+r.failure()?.errorText));
  await page.route(origin+'/**',async route=>{try{const request=route.request(),url=new URL(request.url());
   if(url.pathname==='/api'){
    const envelope=request.postDataJSON();if(envelope.operation!=='projects/invoke')throw Error('알 수 없는 통합 명령');
    const result=await call(envelope.payload);if(result.error)throw Error(result.error);
    return route.fulfill({contentType:'application/json',body:JSON.stringify(result)});
   }
   if(url.pathname==='/favicon.ico')return route.fulfill({status:204});
   if(!url.pathname.startsWith(prefix)){errors.push('원본 화면이 플랫폼 밖의 경로를 요청합니다: '+url.pathname);return route.fulfill({status:404,body:'Mount adapter required'})}
   if(cfg.server_ui){
    const relative=decodeURIComponent(url.pathname.slice(prefix.length));
    if(!relative||relative==='index.html')return route.fulfill({contentType:'text/html',body:cfg.index_html});
    const result=await call({path:'/'+relative,query:url.search.slice(1),method:request.method()});
    if(result.error)throw Error(result.error);
    if(result.status>=400)errors.push('원본 서버 화면 요청 실패: '+url.pathname);
    return route.fulfill({status:result.status,headers:result.headers,body:Buffer.from(result.body,'base64')});
   }
   let relative=decodeURIComponent(url.pathname.slice(prefix.length));let file=path.resolve(cfg.root,relative||'index.html');
   if(!file.startsWith(path.resolve(cfg.root)+path.sep)&&file!==path.resolve(cfg.root))throw Error('프로젝트 밖의 파일 요청');
   if((!fs.existsSync(file)||fs.statSync(file).isDirectory())&&!path.extname(relative))file=path.join(cfg.root,'index.html');
   if(!fs.existsSync(file)||!fs.statSync(file).isFile()){errors.push('원본 화면 요청 실패: '+url.pathname);return route.fulfill({status:404,body:'Not found'})}
   const extension=path.extname(file);const types={'.html':'text/html','.js':'application/javascript','.mjs':'application/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.webp':'image/webp','.woff2':'font/woff2'};
   let body=fs.readFileSync(file);if(file===path.join(cfg.root,'index.html'))body=Buffer.from(cfg.index_html);
   return route.fulfill({contentType:types[extension]||'application/octet-stream',body});
  }catch(e){errors.push(e.message);await route.fulfill({status:500,body:e.message})}});
  await page.goto(origin+prefix+'index.html',{waitUntil:'networkidle',timeout:45000});
  if(!await page.locator('body').isVisible())errors.push('화면 본문이 표시되지 않습니다.');
  const text=(await page.locator('body').innerText()).trim();let media=false;
  for(const element of await page.locator('img,svg,canvas,iframe').all())if(await element.isVisible()){media=true;break}
  if(!text&&!media)errors.push('원본 앱의 화면이 비어 있습니다. 라우팅 어댑터가 필요합니다.');
  await page.screenshot({path:cfg.screenshot,fullPage:false});
  if(errors.length)throw Error([...new Set(errors)].join('\n'));
  console.log('UI_VERIFIED: original page rendered; no JavaScript or resource failures');
 }finally{await browser.close();reader?.close();if(worker){worker.stdin.end();const killer=setTimeout(()=>worker.kill(),3000);killer.unref()}}
}
main().catch(e=>{console.error(e.message);process.exitCode=1});
