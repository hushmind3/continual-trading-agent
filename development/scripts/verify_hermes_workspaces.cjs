// Real registered original UI and Hermes navigation; never submits a model request.
const {chromium}=require('@playwright/test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const origin='http://127.0.0.1:8766',out=path.resolve('runtime/ai_agent/Hermes/verification/workspace-tabs');
async function main(){
 const browser=await chromium.launch({headless:true});fs.mkdirSync(out,{recursive:true});
 let page;
 try{
  page=await browser.newPage({viewport:{width:1440,height:960}});const errors=[],submissions=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api')){const b=r.postDataJSON();if(b?.operation?.endsWith('/chat')||b?.payload?.path?.endsWith('/chat/submit'))submissions.push(b.operation)}});
  await page.goto(origin+'/#ai_agent/Hermes',{waitUntil:'networkidle'});
  const nav=page.getByRole('navigation',{name:'대화 작업 화면'});await nav.waitFor();
  assert.deepEqual(await nav.getByRole('button').allTextContents(),['대화','회사 현황','AI 총괄 대화','업무 실행 기록']);
  const composer=page.locator('textarea:visible').first();await composer.fill('탭을 바꿔도 이 초안은 보존합니다');
  await nav.getByRole('button',{name:'회사 현황',exact:true}).click();
  const frame=page.frameLocator('iframe[title="연결된 회사 운영 화면"]');
  await frame.locator('#overview.on').waitFor();await frame.getByText('AI 조직 · 업무 현황',{exact:true}).waitFor();
  await frame.getByText('CPO · 제품',{exact:true}).waitFor();
  assert.equal(await frame.locator('.side').count(),0);
  await page.screenshot({path:path.join(out,'company-overview.png')});
  await frame.getByRole('button',{name:'CEO와 이야기하기 →',exact:true}).click();
  await nav.locator('button[aria-current="page"]').filter({hasText:'AI 총괄 대화'}).waitFor();
  await frame.locator('#talk.on').waitFor();await frame.locator('#prompt').fill('회사 대화 초안도 보존합니다');
  await frame.locator('#messages').evaluate(node=>{const sample=document.createElement('div');sample.id='workspace-markdown-verification';sample.className='bubble ceo';sample.textContent='## UI Markdown 검사\n\n**강조 확인**\n\n<script>window.UNSAFE_MARKDOWN=1</script>';node.append(sample)});
  await frame.getByRole('heading',{name:'UI Markdown 검사',exact:true}).waitFor();await frame.locator('#workspace-markdown-verification strong').waitFor();assert.equal(await frame.locator('#workspace-markdown-verification script').count(),0);assert.equal(await frame.locator('html').evaluate(()=>window.UNSAFE_MARKDOWN),undefined);await frame.locator('#workspace-markdown-verification').evaluate(node=>node.remove());
  await frame.locator('#messages').evaluate(node=>{const sample=document.createElement('div');sample.id='workspace-link-verification';sample.className='bubble ceo';sample.textContent='[요구사항 보기](/assets/projects/verification/requirements.md)';node.append(sample)});
  assert.equal(await frame.getByRole('link',{name:'요구사항 보기',exact:true}).getAttribute('href'),'/assets/projects/verification/requirements.md');await frame.locator('#workspace-link-verification').evaluate(node=>node.remove());
  await frame.locator('#messages').evaluate(node=>{node.scrollTop=node.scrollHeight});await page.screenshot({path:path.join(out,'ceo-markdown.png')});
  await nav.getByRole('button',{name:'업무 실행 기록',exact:true}).click();await frame.locator('#results.on').waitFor();
  await nav.getByRole('button',{name:'AI 총괄 대화',exact:true}).click();assert.equal(await frame.locator('#prompt').inputValue(),'회사 대화 초안도 보존합니다');
  await nav.getByRole('button',{name:'대화',exact:true}).click();assert.equal(await composer.inputValue(),'탭을 바꿔도 이 초안은 보존합니다');
  await nav.getByRole('button',{name:'회사 현황',exact:true}).click();
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(300);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.ok(await frame.locator('html').evaluate(e=>e.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(out,'company-mobile.png')});
  await page.setViewportSize({width:1440,height:960});await frame.getByRole('button',{name:'모델 연결 관리 ↗',exact:true}).click();
  await page.getByRole('heading',{name:/모델/}).first().waitFor();
  assert.equal(await frame.locator('#setup.on').count(),0);
  assert.deepEqual(errors,[]);assert.deepEqual(submissions,[]);
  const report={original_ui:true,markdown_rendered:true,tabs:4,shared_model_settings:true,hermes_draft_preserved:true,company_draft_preserved:true,viewports:[1440,390],horizontal_overflow:false,js_errors:errors,model_submissions:submissions.length};
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }catch(e){if(page)await page.screenshot({path:path.join(out,'failure.png')});throw e}finally{await browser.close()}
}
main().catch(e=>{console.error(e.message);process.exitCode=1});
