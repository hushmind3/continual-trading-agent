import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'tests',workers:1,timeout:30000,reporter:'line',outputDir:'test-results',use:{baseURL:'http://127.0.0.1:8766',browserName:'chromium',channel:'msedge',viewport:{width:1440,height:960},headless:true}});
