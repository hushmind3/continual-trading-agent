import {defineConfig} from 'vite';
import {fileURLToPath,URL} from 'node:url';
import react from '@vitejs/plugin-react';
import tailwind from '@tailwindcss/vite';
import {hermesOfficialUI,officialAliases} from '../modules/hermes/frontend/official-vite';
export default defineConfig({resolve:{dedupe:['react','react-dom'],alias:{...officialAliases,'@platform':fileURLToPath(new URL('./src',import.meta.url))}},cacheDir:'../node_modules/.cache/vite/frontend',plugins:[hermesOfficialUI(),react(),tailwind()],server:{host:'127.0.0.1',port:5173,strictPort:true,proxy:{'/api':{target:'http://127.0.0.1:8766',changeOrigin:true,ws:true}}},build:{outDir:'dist',emptyOutDir:true}});
