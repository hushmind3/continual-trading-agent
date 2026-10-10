import {defineConfig} from '@playwright/test';
export default defineConfig({
  testDir:'tests',workers:1,timeout:45000,expect:{timeout:15000},reporter:'line',outputDir:'test-results',
  use:{baseURL:process.env.FRONTEND_TEST_URL||'http://127.0.0.1:8766',browserName:'chromium',
    launchOptions:{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE},
    viewport:{width:1440,height:960},headless:true},
});
