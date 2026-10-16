// Actual public GitHub search -> register button -> original UI -> detach, preserving source/settings.
const {chromium}=require('@playwright/test'),fs=require('node:fs'),path=require('node:path');
const base='http://127.0.0.1:8766',folder=path.resolve('runtime/projects/manage/verification');
fs.mkdirSync(folder,{recursive:true});
async function api(operation,payload){const response=await fetch(base+'/api',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({operation,payload:payload||{}})});const result=await response.json();if(!response.ok)throw Error(JSON.stringify(result));return result}
async function main(){const report={checks:[],status:'running'},browser=await chromium.launch({headless:true});
 try{const page=await browser.newPage({viewport:{width:1440,height:1000}});await page.goto(base+'/#projects/manage/search');
  await page.getByRole('textbox',{name:'GitHub 검색어',exact:true}).fill('repo:mdn/beginner-html-site-styled');
  await page.getByRole('button',{name:'검색',exact:true}).click();
  await page.getByRole('link',{name:'mdn/beginner-html-site-styled',exact:true}).waitFor({timeout:35000});
  report.checks.push('Actual GitHub search result rendered');console.log(report.checks.at(-1));
  const existing=(await api('projects/installed')).items.find(item=>item.repository==='mdn/beginner-html-site-styled');
  if(existing&&existing.stage!=='removed'&&(existing.active_source||!['failed','cancelled'].includes(existing.stage)))throw Error('Existing sample installation: do not overwrite user changes');
  await page.locator('article').filter({has:page.getByRole('link',{name:'mdn/beginner-html-site-styled',exact:true})}).getByRole('button',{name:'설치',exact:true}).click();
  let item,last;const deadline=Date.now()+240000;
  while(Date.now()<deadline){try{item=(await api('projects/installed')).items.find(item=>item.repository==='mdn/beginner-html-site-styled');if(item&&item.stage!==last){last=item.stage;console.log('installation: '+item.stage);}
    if(item?.stage==='ready')break;if(['failed','cancelled'].includes(item?.stage))throw Error(item.error||item.detail);
   }catch(e){if(item?.stage==='failed')throw e;}await new Promise(resolve=>setTimeout(resolve,1500));}
  if(item?.stage!=='ready')throw Error('Installation did not finish: '+JSON.stringify(item));
  report.id=item.id;report.checks.push('Actual clone, structure detection, browser execution, automatic menu activation');
  await page.waitForURL(base+'/#'+item.menu,{timeout:20000});await page.getByRole('heading',{name:item.title,exact:true}).waitFor();
  const frame=page.frameLocator('iframe[title="'+item.title+' 원본 화면"]');
  await frame.locator('body').waitFor();const text=await frame.locator('body').innerText();if(!text.includes('Mozilla'))throw Error('Original project UI missing');
  report.checks.push('Original installed UI visible in platform');
  await page.screenshot({path:path.join(folder,'installed-project.png'),fullPage:false});
  const before=fs.existsSync(item.active_source);
  await api('projects/settings',{id:item.id,environment:{PLATFORM_INSTALL_CHECK:'preserved'}});
  await api('projects/remove',{id:item.id});
  report.checks.push('Detach requested through API; source retained');
  if(!before||!fs.existsSync(item.active_source))throw Error('Source lost during detach');
  const record=await api('projects/detail',{id:item.id});if(record.stage!=='removed'||!record.environment_keys.includes('PLATFORM_INSTALL_CHECK'))throw Error('Settings not preserved');
  report.checks.push('Installation record and settings retained');report.status='passed';
 }catch(e){report.status='failed';report.error=e.message;throw e}
 finally{fs.writeFileSync(path.join(folder,'github-install.json'),JSON.stringify(report,null,2));await browser.close()}}
main().catch(e=>{console.error(e);process.exitCode=1});
