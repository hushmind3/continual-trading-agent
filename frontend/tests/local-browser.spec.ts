import {test, expect} from '@playwright/test';

test('all registered local screens render and continue receiving state', async ({page}, testInfo) => {
  test.setTimeout(240_000);
  const errors: string[] = [];
  const failures: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => {if (response.url().includes('/api') && response.status() >= 500) failures.push(`${response.status()} ${response.url()}`);});
  await page.goto('/', {waitUntil: 'networkidle'});
  await expect(page.getByText('서버 연결', {exact: true})).toBeVisible();
  await expect(page.locator('aside a[href="#rea"]')).toBeVisible();
  const links = await page.locator('aside a').evaluateAll(elements => elements
    .map(element => ({href: element.getAttribute('href') || '', name: element.textContent || ''}))
    .filter(element => element.href.startsWith('#')));
  const unique = [...new Map(links.map(link => [link.href, link])).values()];
  expect(unique.length).toBe(11);
  const removed = ['markets','finrl-trading','feature-adaptive_download','feature-adaptive_single','feature-adaptive_backtest','feature-calendar','feature-config_check','portfolio','finrl','stock-training','backtest','feature-finrl_workflow','feature-yahoo','feature-features','feature-data_split','feature-finrl_stats','feature-fundamentals','feature-news','feature-nasdaq100','feature-sp500','feature-process_prices','feature-process_fundamentals','feature-ml_dataset','feature-tsmom','feature-adaptive','feature-equal_weight','feature-ml','feature-sector_ml','feature-performance'];
  expect(unique.filter(link => removed.includes(link.href.slice(1))).map(link => link.href)).toEqual([]);
  for (const link of unique) {
    await page.locator(`aside a[href="${link.href}"]`).click();
    await expect(page.locator('main h1')).toContainText(link.name.trim());
    await expect(page.locator('main')).not.toContainText('통합 API 연결:');
    await expect(page.locator('main')).not.toContainText('화면을 여는 중입니다.');
    await page.screenshot({path: testInfo.outputPath(`${link.href.slice(1)}.png`), fullPage: true});
  }
  expect(errors).toEqual([]);
  expect(failures).toEqual([]);
  console.log(`Verified ${unique.length} live local screens with screenshots, no JS crashes, no HTTP 500`);
});

test('model errors remain visible in MoE and diagnostics without becoming a transport error elsewhere', async ({page}) => {
  await page.route('**/api', async route => {
    const envelope = route.request().postDataJSON();
    if (envelope?.operation !== 'state') { await route.continue(); return; }
    const response = await route.fetch();
    const state = await response.json();
    state.module_errors = {...state.module_errors, 'champion:validation-only': '검증용 모델 형식 오류'};
    await route.fulfill({response, json: state});
  });
  await page.goto('/#control', {waitUntil: 'networkidle'});
  await expect(page.locator('main')).toContainText('다른 기능 오류');
  await expect(page.locator('main')).not.toContainText('검증용 모델 형식 오류');
  await expect(page.locator('main')).not.toContainText('통합 API 연결:');
  await page.locator('aside a[href="#moe"]').click();
  await expect(page.locator('main')).toContainText('검증용 모델 형식 오류');
  await page.locator('aside a[href="#system"]').click();
  await expect(page.locator('main')).toContainText('검증용 모델 형식 오류');
});

test('REA has three input buttons and browses real saved source files without agent controls', async ({page}) => {
  const errors:string[]=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/#rea',{waitUntil:'networkidle'});
  await expect(page.getByRole('button',{name:'파일 선택',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'폴더 선택',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'웹사이트 분석',exact:true}).click();
  await expect(page.getByRole('textbox',{name:'분석할 웹사이트 주소'})).toBeVisible();
  await expect(page.locator('main')).not.toContainText('도구 입력 JSON');
  await expect(page.locator('main')).not.toContainText('AI 재구성');
  await page.locator('aside a[href="#rea-projects"]').click();
  await expect(page.getByRole('combobox',{name:'저장 프로젝트 선택'})).toBeVisible();
  const select=page.getByRole('combobox',{name:'저장 프로젝트 선택'});
  const value=await select.locator('option').evaluateAll(options=>options.map(option=>option as HTMLOptionElement).find(option=>option.value&&option.text.includes('저장 완료'))?.value);
  expect(value).toBeTruthy();
  await select.selectOption(value!);
  await page.getByRole('button',{name:'📄README.md',exact:true}).click();
  await expect(page.locator('main pre')).toContainText('original/');
  await expect(page.getByRole('button',{name:'저장 폴더 열기',exact:true})).toBeEnabled();
  expect(errors).toEqual([]);
});
