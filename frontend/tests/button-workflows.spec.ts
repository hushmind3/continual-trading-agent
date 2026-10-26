import {test,expect,type Page} from '@playwright/test';
import {createServer} from 'node:http';
import {resolve} from 'node:path';

const origin='http://127.0.0.1:8766';
function envelope(request:any){
  if(request.method()==='GET')return {operation:new URL(request.url()).searchParams.get('operation')};
  return request.postDataJSON();
}
async function rejectWrites(page:Page,seen:string[]){
  await page.route('**/api*',async route=>{
    const request=route.request(),body=envelope(request);
    if(request.method()!=='GET'&&body?.operation!=='state'&&body?.operation!=='preflight/train'){
      seen.push(body.operation);
      await route.fulfill({status:400,json:{detail:'버튼 검사: '+body.operation}});
    }else await route.continue();
  });
}

