import {test,expect} from '@playwright/test';

test('MoE explains learning, groups actual roles and filters model families',async({page})=>{
 await page.goto('/#moe');
 const guide=page.locator('details').filter({has:page.getByText('중앙 모델과 Expert · 무엇이 학습되나요?',{exact:true})});
 await guide.locator('summary').click();
 await expect(guide.getByText(/v번호 증가만으로 학습이 진행됐다고/)).toBeVisible();
 await expect(guide.getByText(/중앙 신경망의 자동 용량 확장은 아직/)).toBeVisible();
 await page.getByRole('tab',{name:/^매매 판단/}).click();
 await expect(page.getByRole('button',{name:'FinCast 1.0B 상세',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'FinRL trading bot A2C 상세',exact:true})).toBeVisible();
 await page.getByRole('tab',{name:/^시계열 예측/}).click();
 await expect(page.getByRole('button',{name:'FinCast 1.0B 상세',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'FinRL trading bot A2C 상세',exact:true})).toHaveCount(0);
});

test('process liveness is separate from real inference and learner progress',async({page})=>{
 const state=await (await page.request.get('/api/state')).json();
 state.progress={experts:{code:'progress',label:'실제 처리 증가',service_alive:true,observed_seconds:60,
  counters:{inferences:100,new_inputs:10},changes:{inferences:5,new_inputs:0},last_completed_at:1791516602,detail:'같은 입력 재분석'},
  learner:{code:'waiting',label:'학습 경험 수집 중',service_alive:true,observed_seconds:60,
  counters:{updates:330},changes:{updates:0},last_completed_at:1791516602,detail:'같은 구성 2/4개'}};
 await page.route('**/api/state',r=>r.fulfill({json:state}));await page.goto('/#moe');
 const expert=page.getByTestId('progress-experts'),learner=page.getByTestId('progress-learner');
 await expect(expert.getByText('서비스 켜짐',{exact:true})).toBeVisible();
 await expect(expert.getByText('+5 / 100',{exact:true})).toBeVisible();
 await expect(expert.getByText('+0 / 10',{exact:true})).toBeVisible();
 await expect(learner.getByText('+0 / 330',{exact:true})).toBeVisible();
 await learner.locator('summary').click();await expect(learner.getByText('현재 이유: 같은 구성 2/4개',{exact:true})).toBeVisible();
});

test('failed automatic admission stays visible with the actual blocking cause',async({page})=>{
 const state=await (await page.request.get('/api/state')).json();
 state.library.catalog.admission={id:'unsupported',stage:'blocked',detail:'원본의 뉴스 입력 공급자가 없습니다.',time:1791516602};
 await page.route('**/api/state',r=>r.fulfill({json:state}));await page.goto('/#moe');
 await expect(page.getByText(/자동 추가 차단.*원본의 뉴스 입력 공급자가 없습니다/)).toBeVisible();
});

test('diagnostics shows the backend learning cause instead of a generic wait',async({page,request})=>{
 await page.goto('/#system');
 const state=await (await request.get('/api/state')).json();
 const row=page.getByRole('row').filter({hasText:'TorchRL 학습'});
 await expect(row).toBeVisible();await expect(row.getByText('학습 경험 대기',{exact:true})).toHaveCount(0);
 await expect(row.getByText(state.training.label,{exact:true})).toBeVisible();
});

test('expert conversion exposes four precisions without starting a job',async({page})=>{
 await page.goto('/#moe');await page.getByRole('button',{name:'FinCast 1.0B 정밀도 변환',exact:true}).click();
 const drawer=page.getByRole('dialog');await expect(drawer).toBeVisible();
 for(const precision of ['FP16','BF16','INT8','INT4','NF4'])await expect(drawer.getByRole('button',{name:precision,exact:true})).toBeVisible();
 await drawer.getByRole('button',{name:'INT4',exact:true}).click();
 await expect(drawer.getByRole('button',{name:'INT4',exact:true})).toHaveAttribute('aria-pressed','true');
 await expect(drawer.getByText(/속도 배수로 선택하지 않으며/)).toBeVisible();
 await page.keyboard.press('Escape');await expect(drawer).toHaveCount(0);
});

test('precision variants stay beside their original Expert',async({page,request})=>{
 await page.goto('/#moe');
 const family=page.getByRole('button',{name:'FinCast 1.0B 상세',exact:true});await expect(family).toBeVisible();
 const state=await (await request.get('/api/state')).json();
 if(state.library.catalog.experts.fincast_fp16){
  await expect(family.getByRole('group',{name:'Expert 정밀도 버전'}).getByRole('button',{name:/FP16/})).toBeVisible();
  await expect(page.getByRole('button',{name:'FinCast 1.0B · FP16 상세',exact:true})).toHaveCount(0);
 }
 await expect(family.getByRole('button',{name:'이 Expert 자동 양자화',exact:true})).toBeVisible();
});

test('all precision outcomes expose rejected, failed and absent versions',async({page})=>{
 const state=await (await page.request.get('/api/state')).json();state.library.job={busy:false};
 const base=state.library.catalog.experts.fincast;
 state.library.catalog.optimizations.fincast={stage:'complete',goal:'balanced',previous:'fincast',selected:'fincast',reports:[
  {id:'fincast',precision:'FP32',passed:true,eligible:true,score:1,detail:'원본 비교 기준'},
  {id:'removed_int4',precision:'INT4',passed:false,eligible:false,detail:'상대 RMSE 5% > 1% · 적용 차단',bytes:100,score:.7,measurement:{warm_median_seconds:.1,metrics:{device:'cuda:0'}}}
 ],failures:[{precision:'bf16',detail:'변환 지원 계층 없음'}]};
 for(const [id,item] of Object.entries(state.library.catalog.experts))if((item as any).conversion?.source_id==='fincast'&&['int4','bf16'].includes((item as any).conversion.precision))delete state.library.catalog.experts[id];
 await page.route('**/api/state',route=>route.fulfill({json:state}));
 await page.goto('/#moe');const family=page.getByRole('button',{name:base.name+' 상세',exact:true});
 const versions=family.getByRole('group',{name:'Expert 정밀도 버전'});await expect(versions.locator(':scope > div')).toHaveCount(6);
 await expect(versions.getByText('출력 기준 탈락',{exact:true})).toBeVisible();await expect(versions.getByText('최적화 실패',{exact:true})).toBeVisible();
 await versions.locator(':scope > div').nth(4).getByRole('button',{name:'판단 근거',exact:true}).click();
 const dialog=page.getByRole('dialog');await expect(dialog.getByText('상대 RMSE 5% > 1% · 적용 차단',{exact:true})).toBeVisible();
 await expect(dialog.getByText(/현재 사용할 가중치 파일이 없습니다/)).toBeVisible();await expect(dialog.getByText('0.1s',{exact:true})).toBeVisible();
 await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
 await versions.locator(':scope > div').nth(2).getByRole('button',{name:'판단 근거',exact:true}).click();
 await expect(page.getByRole('dialog').getByText('변환 지원 계층 없음',{exact:true})).toBeVisible();
});

test('public expert discovery displays persisted compatibility and actionable downloads',async({page})=>{
 await page.goto('/#moe');await page.getByRole('button',{name:'금융 Expert 찾기',exact:true}).click();
 const dialog=page.getByRole('dialog');await expect(dialog).toBeVisible();
 await expect(dialog.getByRole('button',{name:'금융 Expert 자동 검색',exact:true})).toBeVisible();
 await dialog.getByText('이름으로 직접 검색',{exact:true}).click();
 await expect(dialog.getByRole('textbox',{name:'공개 모델 검색어'})).toHaveValue('');
 await expect(dialog.getByRole('button',{name:'검색',exact:true})).toBeDisabled();
 const state=await (await page.request.get('/api/state')).json();
 if(state.library.catalog.discovery?.models.length)await expect(dialog.getByRole('link',{name:state.library.catalog.discovery.models[0].repository,exact:true})).toBeVisible();
 await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
});

test('inspection and financial discovery send single complete requests',async({page})=>{
 const actions:{kind:string;payload:unknown}[]=[];
 await page.route('**/api/library/*',async route=>{
  actions.push({kind:route.request().url().split('/').at(-1)!,payload:route.request().postDataJSON()});
  await route.fulfill({json:{accepted:true}});
 });
 await page.goto('/#moe');await page.getByRole('button',{name:'등록 모델 실행 검사',exact:true}).click();
 expect(actions).toEqual([{kind:'probe_all',payload:{device:'auto'}}]);
 await expect(page.getByRole('button',{name:'검사',exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'금융 Expert 찾기',exact:true}).click();
 await page.getByRole('button',{name:'금융 Expert 자동 검색',exact:true}).click();
 expect(actions[1]).toEqual({kind:'search',payload:{preset:'finance',recent_days:365}});
});

test('speed ratios describe the inference duration and discovery keeps dates distinct',async({page})=>{
 const state=await (await page.request.get('/api/state')).json();
 state.library.job={busy:false};
 const variant=Object.values(state.library.catalog.experts).find((e:any)=>e.conversion) as any;
 expect(variant).toBeTruthy();variant.conversion.comparison={speed_ratio:.83};
 state.library.catalog.discovery={query:'금융 Expert 자동 검색',scope:'실제 검사 필요',models:[{
  id:'finance/test@abc',repository:'finance/test',revision:'abc',url:'https://huggingface.co/finance/test',downloads:1,compatible:false,bytes:1048576,
  created:'2024-01-01T00:00:00Z',updated:'2026-10-09T00:00:00Z',release_date:null,detail:'실행기 확인 필요',
  input_summary:'뉴스 텍스트',api_requirement:'미확인',overlap:[],installed_versions:[]
 }]};
 await page.route('**/api/state',route=>route.fulfill({json:state}));
 await page.goto('/#moe');await expect(page.getByText('추론 시간 20.5% 증가 · 느림',{exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'금융 Expert 찾기',exact:true}).click();
 const dialog=page.getByRole('dialog');await expect(dialog.getByText('원본에 날짜 미기재',{exact:false})).toBeVisible();
 await expect(dialog.getByText(/저장소 등록.*2024/)).toBeVisible();await expect(dialog.getByText(/최근 업데이트.*2026/)).toBeVisible();
 await expect(dialog.getByRole('button',{name:'다운로드 · 검사 · 자동 사용',exact:true})).toBeDisabled();
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(391);
});

test('all operating routes, history and direct refresh use the served application',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#control');await expect(page.getByText('실시간 운영',{exact:true})).toBeVisible();
 for(const [name,hash] of [['MoE','moe'],['시장','markets'],['계좌','portfolio'],['학습','learning'],['연결','connection'],['진단','system'],['운영','control']]){
  await page.getByRole('navigation').getByRole('link',{name,exact:true}).click();
  await expect(page).toHaveURL(new RegExp(`#${hash}$`));await expect(page.getByRole('heading',{name,exact:true,level:1})).toBeVisible();
  await page.reload();await expect(page.getByRole('heading',{name,exact:true,level:1})).toBeVisible();
 }
 await page.goBack();await expect(page.getByRole('heading',{name:'진단',exact:true,level:1})).toBeVisible();
 await page.goForward();await expect(page.getByRole('heading',{name:'운영',exact:true,level:1})).toBeVisible();
 expect(errors).toEqual([]);
});

test('legacy hashes resolve immediately to the relevant current workspace',async({page})=>{
 for(const [hash,title] of [['assembly','MoE'],['experts','MoE'],['trading-moe','계좌'],['promotionTrial','학습']]){
  await page.goto(`/#${hash}`);await expect(page.getByRole('heading',{name:title,exact:true,level:1})).toBeVisible();
 }
});

test('market rows select with keyboard and close without losing focus',async({page})=>{
 await page.goto('/#markets');const row=page.locator('tbody tr').first();await expect(row).toBeVisible({timeout:20000});
 await row.focus();await page.keyboard.press('Enter');await expect(page.getByRole('dialog')).toBeVisible();
 await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);await expect(row).toBeFocused();
 await row.click();await expect(page.getByRole('dialog')).toBeVisible();
});

test('expert rows open the selected original asset',async({page})=>{
 await page.goto('/#moe');const row=page.getByRole('button',{name:'FinCast 1.0B 상세',exact:true});await expect(row).toBeVisible();
 await row.focus();await page.keyboard.press('Enter');await expect(page.getByRole('dialog')).toBeVisible();await expect(page.getByText('원본 가중치 고정',{exact:true})).toBeVisible();
});

test('narrow layout exposes all navigation and stays within the viewport',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 for(const hash of ['control','moe','markets','portfolio','learning','connection','system']){
  await page.goto(`/#${hash}`);await expect(page.getByRole('navigation').getByRole('link')).toHaveCount(7);
  await page.waitForTimeout(600);
  const width=await page.evaluate(()=>({page:document.documentElement.scrollWidth,viewport:innerWidth}));expect(width.page).toBeLessThanOrEqual(width.viewport+1);
 }
});

test('opening notifications acknowledges only the displayed event watermark',async({page,request})=>{
 await page.goto('/#control');await expect(page.getByText('서버 연결',{exact:true})).toBeVisible();
 const response=page.waitForResponse(r=>r.url().endsWith('/api/events/read')&&r.request().method()==='POST');
 await page.getByRole('button',{name:/^알림 \d+개$/}).click();
 const read=await response;expect(read.ok()).toBeTruthy();
 const through=read.request().postDataJSON().through;
 await expect(page.getByRole('dialog')).toBeVisible();
 const snapshot=await (await request.get('/api/state')).json();
 expect(snapshot.events.filter((e:{id:number;read:boolean})=>e.id<=through&&!e.read)).toEqual([]);
});

test('paper control changes actual backend state and restores its previous setting',async({page,request})=>{
 const initial=await (await request.get('/api/state')).json();
 test.skip(!initial.controls.engine,'MoE must be running to exercise paper control');
 expect(initial.real_orders_enabled).toBe(false);
 const previous=initial.controls.paper;
 try{
  await page.goto('/#portfolio');
  await page.getByRole('button',{name:previous?'두 계좌 가상체결 정지':'두 계좌 가상체결 시작',exact:true}).click();
  await expect(page.getByRole('button',{name:previous?'두 계좌 가상체결 시작':'두 계좌 가상체결 정지',exact:true})).toBeVisible();
  const changed=await (await request.get('/api/state')).json();
  expect(changed.controls.paper).toBe(!previous);
  expect(changed.controls.feed).toBe(initial.controls.feed);
  expect(changed.controls.engine).toBe(initial.controls.engine);
 }finally{
  const restored=await request.post('/api/controls/paper',{data:{enabled:previous}});
  expect(restored.ok()).toBeTruthy();
 }
});

test('portfolio keeps Korean and US ledgers distinct and exposes missing history',async({page,request})=>{
 await page.goto('/#portfolio');
 await page.getByRole('tab',{name:'미국주식 · USD',exact:true}).click();
 await expect(page.getByRole('heading',{name:'미국주식 · 달러 가상계좌',exact:true})).toBeVisible();
 await page.getByRole('tab',{name:'체결 원장',exact:true}).click();
 await expect(page.getByText('미국주식 · 달러 가상계좌 체결 원장',{exact:true})).toBeVisible();
 const usd=await (await request.get('/api/fills?currency=USD')).json();
 expect(usd.fills.every((f:{currency:string})=>f.currency==='USD')).toBeTruthy();
 if(usd.missing)await expect(page.getByText(/이전 체결 .*기존 공용 기록이 삭제/)).toBeVisible();
 await page.getByRole('tab',{name:'국내주식 · KRW',exact:true}).click();
 await expect(page.getByRole('heading',{name:'국내주식 · 원화 가상계좌',exact:true})).toBeVisible();
 await expect(page.getByText('국내주식 · 원화 가상계좌 체결 원장',{exact:true})).toBeVisible();
 const krw=await (await request.get('/api/fills?currency=KRW')).json();
 expect(krw.fills.every((f:{currency:string})=>f.currency==='KRW')).toBeTruthy();
 if(krw.recorded>50){await expect(page.locator('tbody tr')).toHaveCount(50);await page.getByRole('button',{name:'이전 체결 더 보기'}).click();await expect(page.locator('tbody tr')).toHaveCount(100)}
});

test('positions show an empty account or select a holding with keyboard',async({page})=>{
 await page.goto('/#portfolio');await page.getByRole('tab',{name:'국내주식 · KRW',exact:true}).click();
 const state=await (await page.request.get('/api/state')).json();
 if(!state.account?.books.KRW.positions.length){await expect(page.getByText('이 계좌의 보유 종목이 없습니다.',{exact:true})).toBeVisible();return}
 const row=page.locator('tbody tr').first();await expect(row).toBeVisible();await row.focus();await page.keyboard.press('Enter');
 await expect(page.getByRole('dialog')).toBeVisible();await page.keyboard.press('Escape');await expect(row).toBeFocused();
});
