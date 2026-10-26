import {defineConfig} from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 90_000,
  workers: 1,
  reporter: [['list'], ['html', {open: 'never'}]],
  use: {baseURL: process.env.PLATFORM_BASE_URL || 'http://127.0.0.1:8766', headless: true, trace: 'retain-on-failure', screenshot: 'only-on-failure'},
  projects: [
    {name: 'api', testMatch: /api\.spec\.ts/},
    {name: 'local-browser', testMatch: /(local-browser|button-workflows)\.spec\.ts/},
  ],
});
