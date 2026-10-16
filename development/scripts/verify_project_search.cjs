// Actual installed REA MCP UI and live paginated GitHub search; no external writes.
const {chromium}=require('@playwright/test');
const path=require('node:path');
const fs=require('node:fs');
(async()=>{
 const output=path.resolve('runtime/projects/manage/verification');fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',error=>errors.push(String(error)));
 await page.addInitScript(()=>localStorage.setItem('projects.korean','false'));
 const result={};
 try{
  await page.goto('http://127.0.0.1:8766/?screen=projects#projects/manage/search');
  await page.getByLabel('GitHub 검색어').fill('react');
  await page.getByRole('button',{name:'검색',exact:true}).click();
  await page.getByText(/30개 표시/).waitFor({timeout:45000});
  await page.getByRole('button',{name:'검색 결과 더 보기',exact:true}).click();
  await page.getByText(/60개 표시/).waitFor({timeout:45000});result.search_pages=2;result.results=60;
  await page.goto('http://127.0.0.1:8766/#projects/app/p_morluto_rea_a5b6cf30');
  await page.getByLabel('작업 요청').waitFor({timeout:30000});result.task_ui=true;
  await page.getByRole('button',{name:'개발자용 도구 상세',exact:true}).click();
  await page.getByLabel('MCP 도구').locator('option').first().waitFor({state:'attached',timeout:90000});
  result.mcp_tools=await page.getByLabel('MCP 도구').locator('option').count();
  await page.screenshot({path:path.join(output,'rea-installed.png'),fullPage:true});
  if(errors.length)throw Error(errors.join('\n'));
  result.javascript_errors=errors;result.passed=true;
 }finally{fs.writeFileSync(path.join(output,'search-and-rea.json'),JSON.stringify(result,null,2));await browser.close()}
 console.log(JSON.stringify(result));
})().catch(error=>{console.error(error);process.exitCode=1});
