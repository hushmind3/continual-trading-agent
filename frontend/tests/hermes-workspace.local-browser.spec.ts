import {test,expect,type Page} from '@playwright/test';

const id='hermes-design-fixture';
const rich=[
 '## 작업 결과',
 '**중요한 내용**을 읽기 쉬운 답변으로 정리했습니다.',
 '- 첫 번째 항목\n- 두 번째 항목',
 '| 항목 | 결과 | 비고 |\n| --- | --- | --- |\n| 대화 | 정상 | 넓은 화면 |\n| 도구 | 확인 | 실제 결과 |',
 '\n\x60\x60\x60typescript\nconst longLine = "'+ 'x'.repeat(260)+'";\nconsole.log(longLine);\n\x60\x60\x60',
 '[공식 문서](https://example.com/docs)',
 '[오류 보고서](development/docs/error_mining_report.md)',
 '<img src="invalid" onerror="window.hermesUnsafe=true">'
].join('\n\n');
const messages:Record<string,unknown>[]=[{role:'user',content:'화면 구성과 확인 결과를 정리해 줘.'},{role:'assistant',content:rich}];
for(let i=0;i<3;i++){messages.push({role:'assistant',content:'',tool_calls:[{id:'tool-'+i,type:'function',function:{name:'read_file',arguments:JSON.stringify({path:'example-'+i+'.txt'})}}]},{role:'tool',tool_call_id:'tool-'+i,content:JSON.stringify({success:true,content:'확인된 파일 내용 '+i})})}
messages.push({role:'assistant',content:'모든 결과를 확인했습니다.'});
const settings={base_url:'http://127.0.0.1:1234/v1',model:'Ornith · 화면 확인',api_key:'',has_api_key:false,workspace:'C:/workspace',max_iterations:20,toolsets:['file','computer_use'],local_model:'C:/models/ornith.gguf',python:'3.14',engine:'fixture',available_toolsets:['file','computer_use'],computer_driver_installed:true,browser_runtime_installed:true};

async function fixture(page:Page,empty=false,history=false){
 const calls:{op:string;payload:Record<string,unknown>}[]=[];
 const state={job:{state:'complete',session_id:id,text:'',error:'',events:[{name:'tool_start',detail:JSON.stringify(['step-1','read_file',{path:'example.txt'}]),time:1},{name:'tool_complete',detail:JSON.stringify(['step-1','read_file',{path:'example.txt'},JSON.stringify({success:true,content:'확인된 내용'})]),time:2}],metrics:{context_limit:65536,context_tokens:24576,generation_tps:58.6,input_tokens:25000,output_tokens:720,api_calls:3,elapsed_seconds:18},approval:undefined as undefined|{kind:string;detail:string}}};
 await page.route('**/api**',async route=>{
  const r=route.request(),url=new URL(r.url());let op:string,payload:Record<string,unknown>;
  try{if(r.method()==='GET'){op=url.searchParams.get('operation')??'';payload=JSON.parse(url.searchParams.get('payload')??'{}')}else{const body=r.postDataJSON();op=body.operation;payload=body.payload??{}}}catch{return route.continue()}
  if(!op.startsWith('ai_agent/Hermes/'))return route.continue();
  op=op.slice('ai_agent/Hermes/'.length);calls.push({op,payload});let response:unknown={};
  const status=()=>({job:{...state.job},local_model:{running:true,state:'ready',base_url:settings.base_url}});
  if(history)state.job.events=[];
  if(op==='status')response=status();
  else if(op==='settings')response={...settings,...(payload.system_prompt!==undefined?{system_prompt:payload.system_prompt}:{}),...(payload.read_only!==undefined?{read_only:payload.read_only}:{})};
  else if(op==='sessions'&&empty)response=state.job.state==='running'?[{id:'new-chat-session',title:'새 대화 검증',model:settings.model}]:[];
  else if(op==='sessions')response=[{id,title:'대화 디자인 점검',model:settings.model},{id:'another-session',title:'다른 프로젝트',model:settings.model}];
  else if(op==='session')response={session:{id:payload.id,title:payload.id===id?'대화 디자인 점검':'다른 프로젝트',model:settings.model},messages:payload.id===id?messages:[]};
  else if(op==='autonomy')response={goal:null,loop:null};
  else if(op==='artifact/upload')response={name:payload.name,path:'C:/workspace/runtime/ai_agent/Hermes/artifacts/uploads/test/'+payload.name,bytes:8};
  else if(op==='artifact'&&payload.path==='missing.md'){await route.fulfill({status:404,json:{detail:'문서 파일이 없습니다.'}});return}
  else if(op==='artifact')response={name:'error_mining_report.md',path:String(payload.path),format:'.md',bytes:90,content:'# 검사 보고서\n\n- 재시작 보호 확인\n\n<script>window.reportUnsafe=true</script>',truncated:false};
  else if(op==='models/local')response={models:[],root:'C:/models'};
  else if(op==='models')response={models:[]};
  else if(op==='chat'){state.job={...state.job,state:'running',session_id:String(payload.session_id||(empty?'new-chat-session':id))};response=status()}
  else if(op==='stop'){state.job={...state.job,state:'stopped'};response=status()}
  else if(op==='answer'){delete state.job.approval;response=status()}
  else if(op==='skills')response={skills:[]};
  else if(op==='mcp/catalog')response={entries:[],installation:{state:'idle',name:'',error:''}};
  else if(op==='mcp')response={servers:{},status:[]};
  await route.fulfill({json:response});
 });
 await page.goto('/#ai_agent/Hermes');
 if(!empty)await expect(page.locator('.ha-markdown h2')).toHaveText('작업 결과');
 return {calls,state};
}

test('rich answers, tools only in activity panel, copy, reading position and full-focus layout',async({page,context})=>{
 await context.grantPermissions(['clipboard-read','clipboard-write']);
 await page.setViewportSize({width:1440,height:720});
 await fixture(page);
 await expect(page.locator('.ha-markdown strong')).toHaveText('중요한 내용');
 await expect(page.locator('.ha-table-scroll table')).toHaveCount(1);
 await expect(page.locator('.ha-code-block')).toHaveCount(1);
 await expect(page.locator('.ha-markdown img')).toHaveCount(0);
 expect(await page.evaluate(()=>Boolean((window as unknown as Record<string,unknown>).hermesUnsafe))).toBe(false);
 await expect(page.locator('.hermes-messages .ha-tool-group')).toHaveCount(0);
 await expect(page.locator('.ha-composer-dock .hermes-current-activity')).toHaveCount(0);
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
 expect(await page.locator('.hermes-workspace').evaluate(el=>({x:el.getBoundingClientRect().x,y:el.getBoundingClientRect().y,width:el.clientWidth,height:el.clientHeight}))).toEqual({x:0,y:0,width:1440,height:720});
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


test('system prompt settings save only the prompt and preserve the chat',async({page})=>{
 const {calls}=await fixture(page);
 await page.getByRole('button',{name:'설정 열기',exact:true}).click();
 await page.getByRole('button',{name:'시스템 프롬프트',exact:true}).click();
 const editor=page.getByRole('textbox',{name:'시스템 프롬프트',exact:true});
 await expect(editor).toBeEnabled();
 await page.getByRole('checkbox',{name:'읽기 전용 분석'}).check();
 await editor.fill('한국어로 답하고 실제 도구 결과를 확인하세요.');
 await page.getByRole('button',{name:'시스템 프롬프트 저장',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('다음 대화 요청부터 적용됩니다.');
 expect(calls.filter(call=>call.op==='settings'&&Object.keys(call.payload).length).at(-1)?.payload).toEqual({system_prompt:'한국어로 답하고 실제 도구 결과를 확인하세요.',read_only:true});
 await page.getByRole('button',{name:'대화로 돌아가기',exact:true}).click();
 await expect(page.locator('.ha-markdown h2')).toHaveText('작업 결과');
});


test('repeated message stays visible until that new turn is persisted',async({page})=>{
 await fixture(page);
 const users=page.locator('.hermes-message.user');
 const before=await users.count();
 await page.getByLabel('헤르메스에게 보낼 메시지').fill('화면 구성과 확인 결과를 정리해 줘.');
 await page.getByLabel('헤르메스에게 보낼 메시지').press('Enter');
 await expect(users).toHaveCount(before+1);
});

test('first chat persists its new session and restores it after reload',async({page})=>{
 await fixture(page,true);
 const editor=page.getByLabel('헤르메스에게 보낼 메시지');
 await editor.fill('새 세션을 만듭니다.');await editor.press('Enter');
 await expect.poll(()=>page.evaluate(()=>sessionStorage.getItem('hermes.session'))).toBe('new-chat-session');
 await page.reload();
 await expect(page.locator('.hermes-chat-heading')).toContainText('새 대화 검증');
});


test('local report links open readable documents inside the chat',async({page})=>{
 await page.setViewportSize({width:1440,height:900});
 const {calls}=await fixture(page);
 await page.getByRole('button',{name:'오류 보고서',exact:true}).click();
 const dialog=page.getByRole('complementary',{name:'결과 문서'});
 await expect(dialog.getByRole('heading',{name:'검사 보고서'})).toBeVisible();
 const before=(await dialog.boundingBox())!;
 await dialog.getByRole('button',{name:'문서 패널 축소'}).click();
 await expect.poll(async()=>(await dialog.boundingBox())!.width).toBeLessThan(before.width);
 expect((await dialog.getByRole('button',{name:'문서 닫기'}).boundingBox())!.x).toBeLessThan(1440);
 await dialog.getByRole('button',{name:'문서 패널 확대'}).click();
 await expect(dialog).toContainText('재시작 보호 확인');
 await expect(page.getByRole('dialog')).toHaveCount(0);
 await expect(page.getByLabel('헤르메스에게 보낼 메시지')).toBeEditable();
 await dialog.getByRole('button',{name:'소스',exact:true}).click();
 await expect(dialog.locator('pre')).toContainText('# 검사 보고서');
 expect(await page.evaluate(()=>Boolean((window as unknown as Record<string,unknown>).reportUnsafe))).toBe(false);
 expect(calls.some(call=>call.op==='artifact'&&call.payload.path==='development/docs/error_mining_report.md')).toBe(true);
 await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
 await expect(page.getByRole('button',{name:'오류 보고서',exact:true})).toBeFocused();
});

test('historical tools use one flat activity list with visible file names',async({page})=>{
 await fixture(page,false,true);
 await page.getByRole('button',{name:'작업 내역 보기',exact:true}).click();
 await expect(page.locator('.hermes-log .ha-tool-group')).toHaveCount(0);
 await expect(page.locator('.hermes-log .ha-activity-item')).toHaveCount(3);
 await expect(page.locator('.hermes-log summary').filter({hasText:'example-0.txt'})).toBeVisible();
 await expect(page.locator('.hermes-log details details')).toHaveCount(0);
 await page.locator('.hermes-log .ha-activity-item>summary').first().click();
 await expect(page.locator('.hermes-log pre').filter({hasText:'확인된 파일 내용 0'})).toBeVisible();
});

test('upload attaches a real file reference and next run mode stays editable during work',async({page})=>{
 const {calls}=await fixture(page);
 await page.getByLabel('첨부 파일 선택',{exact:true}).setInputFiles({name:'요청.md',mimeType:'text/markdown',buffer:Buffer.from('# 요청')});
 await expect(page.getByLabel('첨부 파일',{exact:true})).toContainText('요청.md');
 await page.getByRole('button',{name:'메시지 보내기',exact:true}).click();
 await expect.poll(()=>calls.filter(call=>call.op==='chat').length).toBe(1);
 const sent=calls.find(call=>call.op==='chat')!;
 expect(sent.payload.attachments).toEqual(['C:/workspace/runtime/ai_agent/Hermes/artifacts/uploads/test/요청.md']);
 expect(sent.payload.message).toContain('[요청.md]');
 await expect(page.getByLabel('실행 방식',{exact:true})).toBeEnabled();
 await page.getByLabel('실행 방식',{exact:true}).selectOption('goal');
 await expect(page.getByLabel('목표 최대 대화 수')).toBeEnabled();
 expect(calls.filter(call=>call.op==='chat')).toHaveLength(1);
});

test('missing document leaves the full conversation usable instead of opening an empty pane',async({page})=>{
 await fixture(page);
 await page.route('**/api**',async(route)=>{const request=route.request();const op=request.method()==='POST'?request.postDataJSON()?.operation:new URL(request.url()).searchParams.get('operation');if(op==='ai_agent/Hermes/artifact')return route.fulfill({status:404,json:{detail:'문서 파일이 없습니다.'}});return route.fallback()});
 await page.getByRole('button',{name:'오류 보고서',exact:true}).click();
 await expect(page.getByRole('alert')).toContainText('문서 파일이 없습니다.');
 await expect(page.getByRole('complementary',{name:'결과 문서'})).toHaveCount(0);
 await expect(page.getByLabel('헤르메스에게 보낼 메시지')).toBeEditable();
});
