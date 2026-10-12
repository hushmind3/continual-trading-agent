import {test, expect} from '@playwright/test';

test('all registered local screens render and continue receiving state', async ({page}, testInfo) => {
  test.setTimeout(240_000);
  const errors: string[] = [];
  const failures: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => {if (response.url().includes('/api') && response.status() >= 500) failures.push(`${response.status()} ${response.url()}`);});
  await page.goto('/', {waitUntil: 'networkidle'});
  await expect(page.getByText('서버 연결', {exact: true})).toBeVisible();
  const links = await page.locator('aside a').evaluateAll(elements => elements
    .map(element => ({href: element.getAttribute('href') || '', name: element.textContent || ''}))
    .filter(element => element.href.startsWith('#')));
  const unique = [...new Map(links.map(link => [link.href, link])).values()];
  expect(unique.length).toBeGreaterThanOrEqual(15);
  for (const link of unique) {
    await page.locator(`aside a[href="${link.href}"]`).click();
    await expect(page.locator('main h1')).toContainText(link.name.trim());
    await expect(page.locator('main')).not.toContainText('통합 API 연결:');
    await expect(page.locator('main')).not.toContainText('화면을 여는 중입니다.');
    await page.screenshot({path: testInfo.outputPath(`${link.href.slice(1)}.png`), fullPage: true});
  }
  expect(errors).toEqual([]);
  expect(failures).toEqual([]);
  await page.locator('aside a[href="#markets"]').click();
  await expect(page.locator('main')).toContainText('시장 · 실제 가격 저장소');
  const next = page.getByRole('button', {name: '다음', exact: true});
  if (await next.isEnabled()) {
    await next.click();
    await expect(page.locator('main')).toContainText('2 /');
  }
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
  await page.goto('/#markets', {waitUntil: 'networkidle'});
  await expect(page.locator('main')).toContainText('다른 기능 오류');
  await expect(page.locator('main')).not.toContainText('검증용 모델 형식 오류');
  await expect(page.locator('main')).not.toContainText('통합 API 연결:');
  await page.locator('aside a[href="#moe"]').click();
  await expect(page.locator('main')).toContainText('검증용 모델 형식 오류');
  await page.locator('aside a[href="#system"]').click();
  await expect(page.locator('main')).toContainText('검증용 모델 형식 오류');
});
