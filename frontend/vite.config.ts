import {defineConfig} from 'vite';
import {fileURLToPath,URL,pathToFileURL} from 'node:url';
import {existsSync} from 'node:fs';
import react from '@vitejs/plugin-react';
import tailwind from '@tailwindcss/vite';
export default defineConfig(async()=>{const path=fileURLToPath(new URL('../modules/hermes/frontend/official-vite.ts',import.meta.url));const native=existsSync(path)?await import(/* @vite-ignore */ pathToFileURL(path).href):null;return {resolve:{dedupe:['react','react-dom'],alias:{...(native?.officialAliases??{}),'@platform':fileURLToPath(new URL('./src',import.meta.url))}},cacheDir:'../node_modules/.cache/vite/frontend',plugins:[...(native?[native.hermesOfficialUI()]:[]),react(),tailwind()],server:{host:'127.0.0.1',port:5173,strictPort:true,proxy:{'/api':{target:'http://127.0.0.1:8766',changeOrigin:true,ws:true}}},build:{outDir:'dist',emptyOutDir:true}}});
