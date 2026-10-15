import {test,expect,type Page} from '@playwright/test';

const id='hermes-design-fixture';
const rich=[
 '## 작업 결과',
 '**중요한 내용**을 읽기 쉬운 답변으로 정리했습니다.',
 '- 첫 번째 항목\n- 두 번째 항목',
 '| 항목 | 결과 | 비고 |\n| --- | --- | --- |\n| 대화 | 정상 | 넓은 화면 |\n| 도구 | 확인 | 실제 결과 |',
 '\n\x60\x60\x60typescript\nconst longLine = "'+ 'x'.repeat(260)+'";\nconsole.log(longLine);\n\x60\x60\x60',
 '[공식 문서](https://example.com/docs)',
 '<img src="invalid" onerror="window.hermesUnsafe=true">'
].join('\n\n');
const messages:Record<string,unknown>[]=[{role:'user',content:'화면 구성과 확인 결과를 정리해 줘.'},{role:'assistant',content:rich}];
for(let i=0;i<3;i++){messages.push({role:'assistant',content:'',tool_calls:[{id:'tool-'+i,type:'function',function:{name:'read_file',arguments:JSON.stringify({path:'example-'+i+'.txt'})}}]},{role:'tool',tool_call_id:'tool-'+i,content:JSON.stringify({success:true,content:'확인된 파일 내용 '+i})})}
messages.push({role:'assistant',content:'모든 결과를 확인했습니다.'});
const settings={base_url:'http://127.0.0.1:1234/v1',model:'Ornith · 화면 확인',api_key:'',has_api_key:false,workspace:'C:/workspace',max_iterations:20,toolsets:['file','computer_use'],local_model:'C:/models/ornith.gguf',python:'3.14',engine:'fixture',available_toolsets:['file','computer_use'],computer_driver_installed:true,browser_runtime_installed:true};

async function fixture(page:Page){
 const calls:{op:string;payload:Record<string,unknown>}[]=[];
 const state={job:{state:'complete',session_id:id,text:'',error:'',events:[{name:'tool_start',detail:JSON.stringify(['step-1','read_file',{path:'example.txt'}]),time:1},{name:'tool_complete',detail:JSON.stringify(['step-1','read_file',{path:'example.txt'},JSON.stringify({success:true,content:'확인된 내용'})]),time:2}],metrics:{context_limit:65536,context_tokens:24576,generation_tps:58.6,input_tokens:25000,output_tokens:720,api_calls:3,elapsed_seconds:18},approval:undefined as undefined|{kind:string;detail:string}}};
 await page.route('**/api**',async route=>{
  const r=route.request(),url=new URL(r.url());let op:string,payload:Record<string,unknown>;
  try{if(r.method()==='GET'){op=url.searchParams.get('operation')??'';payload=JSON.parse(url.searchParams.get('payload')??'{}')}else{const body=r.postDataJSON();op=body.operation;payload=body.payload??{}}}catch{return route.continue()}
  if(!op.startsWith('ai_agent/Hermes/'))return route.continue();
  op=op.slice('ai_agent/Hermes/'.length);calls.push({op,payload});let response:unknown={};
  const status=()=>({job:{...state.job},local_model:{running:true,state:'ready',base_url:settings.base_url}});
  if(op==='status')response=status();
  else if(op==='settings')response=settings;
  else if(op==='sessions')response=[{id,title:'대화 디자인 점검',model:settings.model},{id:'another-session',title:'다른 프로젝트',model:settings.model}];
  else if(op==='session')response={session:{id:payload.id,title:payload.id===id?'대화 디자인 점검':'다른 프로젝트',model:settings.model},messages:payload.id===id?messages:[]};
  else if(op==='autonomy')response={goal:null,loop:null};
  else if(op==='models/local')response={models:[],root:'C:/models'};
  else if(op==='models')response={models:[]};
  else if(op==='chat'){state.job={...state.job,state:'running',session_id:String(payload.session_id||id)};response=status()}
  else if(op==='stop'){state.job={...state.job,state:'stopped'};response=status()}
  else if(op==='answer'){delete state.job.approval;response=status()}
  else if(op==='skills')response={skills:[]};
  else if(op==='mcp/catalog')response={entries:[],installation:{state:'idle',name:'',error:''}};
  else if(op==='mcp')response={servers:{},status:[]};
  await route.fulfill({json:response});
 });
 await page.goto('/#ai_agent/Hermes');
 await expect(page.locator('.ha-markdown h2')).toHaveText('작업 결과');
 return {calls,state};
}

test('rich answers, grouped tools, copy, reading position and full-focus layout',async({page,context})=>{
 await context.grantPermissions(['clipboard-read','clipboard-write']);
 await page.setViewportSize({width:1440,height:1000});
 await fixture(page);
 await expect(page.locator('.ha-markdown strong')).toHaveText('중요한 내용');
 await expect(page.locator('.ha-table-scroll table')).toHaveCount(1);
 await expect(page.locator('.ha-code-block')).toHaveCount(1);
 await expect(page.locator('.ha-markdown img')).toHaveCount(0);
 expect(await page.evaluate(()=>Boolean((window as unknown as Record<string,unknown>).hermesUnsafe))).toBe(false);
 await expect(page.locator('.ha-tool-group')).toHaveCount(1);
 await expect(page.locator('.ha-tool-group>summary')).toContainText('3');
 await page.locator('.ha-tool-group>summary').click();
 await expect(page.locator('.ha-tool-step')).toHaveCount(3);
 await expect(page.locator('.hermes-runtime-metrics')).toContainText('58.6 tok/s');
 await page.getByRole('button',{name:'작업 내역 보기',exact:true}).click();
 await expect(page.locator('.ha-activity-item')).toHaveCount(1);
 await expect(page.locator('.ha-activity-item')).toContainText('파일 읽기');
 await expect(page.locator('.ha-activity-item')).toContainText('결과 수신');
 await page.getByRole('button',{name:'작업 내역 닫기',exact:true}).click();
 await expect(page.locator('.hermes-chat-heading .hermes-runtime-metrics')).toBeVisible();
 await expect(page.locator('.hermes-runtime-metrics').getByText('25,000',{exact:true})).toBeVisible();
 await expect(page.locator('.hermes-runtime-metrics details')).toHaveCount(0);
 await page.locator('.hermes-messages').evaluate(el=>{el.scrollTop=0;el.dispatchEvent(new Event('scroll',{bubbles:true}))});
 await expect(page.getByLabel('최신 메시지로 이동')).toBeVisible();
 await page.getByRole('button',{name:'코드 복사',exact:true}).click();
 expect(await page.evaluate(()=>navigator.clipboard.readText())).toContain('const longLine');
 await page.getByRole('button',{name:'집중 모드 켜기',exact:true}).click();
 expect(await page.locator('.hermes-workspace').evaluate(el=>({x:el.getBoundingClientRect().x,y:el.getBoundingClientRect().y,width:el.clientWidth,height:el.clientHeight}))).toEqual({x:0,y:0,width:1440,height:1000});
 await page.getByRole('button',{name:'집중 모드 나가기',exact:true}).click();
 expect(await page.locator('.hermes-workspace').evaluate(el=>el.getBoundingClientRect().x)).toBeGreaterThan(0);
});

test('session search, per-session drafts and settings preserve the conversation',async({page})=>{
 await page.setViewportSize({width:1440,height:1000});await fixture(page);
 const editor=page.getByLabel('헤르메스에게 보낼 메시지');
 await editor.fill('작성 중인 메시지를 보존합니다.');
 await page.getByRole('button',{name:'설정 열기',exact:true}).click();
 await expect(page.getByRole('navigation',{name:'헤르메스 설정'})).toBeVisible();
 await page.getByRole('button',{name:'MCP',exact:true}).click();
 await expect(page.locator('.ha-settings-section-title h2')).toHaveText('MCP');
 await page.getByRole('button',{name:'스킬',exact:true}).click();
 await expect(page.locator('.ha-settings-section-title h2')).toHaveText('스킬');
 await page.getByRole('button',{name:'대화로 돌아가기',exact:true}).click();
 await expect(editor).toHaveValue('작성 중인 메시지를 보존합니다.');
 await page.getByRole('button',{name:'대화 기록 열기',exact:true}).click();
 await page.getByLabel('대화 검색',{exact:true}).fill('다른');
 await expect(page.locator('.hermes-session-list>button')).toHaveCount(1);
 await page.getByRole('button',{name:'다른 프로젝트',exact:true}).click();
 await expect(editor).toHaveValue('');
 await editor.fill('다른 세션의 초안');
 await page.getByLabel('대화 검색',{exact:true}).fill('디자인');
 await page.getByRole('button',{name:'대화 디자인 점검',exact:true}).click();
 await expect(editor).toHaveValue('작성 중인 메시지를 보존합니다.');
 await page.reload();await expect(editor).toHaveValue('작성 중인 메시지를 보존합니다.');
});

test('responsive layout, mobile drawer escape and keyboard focus',async({page})=>{
 await page.setViewportSize({width:390,height:844});await fixture(page);
 for(const [width,height] of [[360,740],[390,844],[768,900],[1024,768],[1440,1000],[1920,1080]]){
  await page.setViewportSize({width,height});
  const bounds=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,page:document.documentElement.scrollHeight,composer:document.querySelector('.hermes-composer')!.getBoundingClientRect().bottom,messageHeight:document.querySelector('.hermes-messages')!.clientHeight}));
  expect(bounds.overflow,'horizontal overflow at '+width).toBe(false);
  expect(bounds.page).toBeLessThanOrEqual(height+1);
  expect(bounds.composer).toBeLessThanOrEqual(height);
  expect(bounds.messageHeight).toBeGreaterThan(300);
 }
 await page.setViewportSize({width:390,height:844});
 const opener=page.getByRole('button',{name:'대화 기록 열기',exact:true});await opener.click();
 await expect(page.getByRole('complementary',{name:'대화 기록',exact:true})).toBeVisible();
 await page.keyboard.press('Escape');await expect(opener).toBeFocused();
 await page.getByRole('button',{name:'작업 내역 보기',exact:true}).click();
 await expect(page.getByRole('complementary',{name:'작업 내역',exact:true})).toBeVisible();
 await page.keyboard.press('Escape');
 await expect(page.getByRole('button',{name:'작업 내역 보기',exact:true})).toBeFocused();
});

test('goal send, stop and approval controls use the existing API contract',async({page})=>{
 const {calls,state}=await fixture(page);
 await page.getByLabel('실행 방식',{exact:true}).selectOption('goal');
 await page.getByLabel('목표 최대 대화 수').fill('7');
 await page.getByLabel('헤르메스에게 보낼 메시지').fill('프론트 기능 확인용 작업');
 await page.getByRole('button',{name:'메시지 보내기',exact:true}).click();
 await expect.poll(()=>calls.find(c=>c.op==='chat')?.payload.mode).toBe('goal');
 expect(calls.find(c=>c.op==='chat')?.payload.max_turns).toBe(7);
 await page.getByRole('button',{name:'작업 중지',exact:true}).click();
 await expect.poll(()=>calls.filter(c=>c.op==='stop').length).toBe(1);
 state.job={...state.job,state:'running',approval:{kind:'question',detail:'확인할 질문'}};
 await page.reload();await page.getByLabel('헤르메스 질문에 답변').fill('승인된 답변');
 await page.getByRole('button',{name:'답변 보내기',exact:true}).click();
 await expect.poll(()=>calls.find(c=>c.op==='answer')?.payload.text).toBe('승인된 답변');
 expect(calls.find(c=>c.op==='answer')?.payload.allow).toBe(true);
});
