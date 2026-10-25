import {readFileSync} from 'node:fs';
import {existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import type {Plugin} from 'vite';

const here=(path:string)=>fileURLToPath(new URL(path,import.meta.url));
const sharedPackage=here('../backend/engine/upstream/apps/shared/package.json');
const sharedExports=JSON.parse(readFileSync(sharedPackage,'utf8')).exports as Record<string,string>;
const sharedAliases=Object.fromEntries(Object.entries(sharedExports).sort(([a],[b])=>b.length-a.length).map(([key,value])=>['@hermes/shared'+key.slice(1),here('../backend/engine/upstream/apps/shared/'+value)]));
export const officialAliases={
 '@hermes-official':here('../backend/engine/upstream/web/src'),
 ...sharedAliases,
 '@':here('../backend/engine/upstream/web/src'),
 'react-router':here('../backend/engine/upstream/web/node_modules/react-router'),
};

/** Adapt UI transport/import boundaries without forking the official feature code. */
export function hermesOfficialUI():Plugin{
 const native=here('../backend/engine/upstream/web/src/').replaceAll('\\','/');
 return {name:'hermes-platform-integration',enforce:'pre',
  buildStart(){
   const patch=here('../backend/engine/patches/platform.patch');
   if(!existsSync(patch))return;
   const cwd=here('../backend/engine/upstream');
   const args=['apply','--ignore-space-change'];
   if(spawnSync('git',[...args,'--reverse','--check',patch],{cwd,windowsHide:true}).status===0)return;
   const check=spawnSync('git',[...args,'--check',patch],{cwd,windowsHide:true,encoding:'utf8'});
   if(check.status!==0)this.error('공식 코드와 플랫폼 패치가 충돌합니다. '+check.stderr);
   if(spawnSync('git',[...args,patch],{cwd,windowsHide:true}).status!==0)this.error('플랫폼 한글·호환 패치를 적용하지 못했습니다.');
  },
  resolveId(source){if(source==='hermes-platform-transport')return here('./settings/official/transport.ts')},
  transform(code,id){
   const path=id.replaceAll('\\','/').split('?')[0];
   if(!path.startsWith(native)||!/[cm]?[jt]sx?$/.test(path))return;
   const imports:string[]=[];
   if(path.endsWith('/plugins/usePlugins.ts')){
    code=code.replace('return `${HERMES_BASE_PATH}/dashboard-plugins/${scope}${name}/${file}`;', 'return officialAssetUrl(`/dashboard-plugins/${scope}${name}/${file}`);');
    imports.push('officialAssetUrl');
   }
   if(/(?<![\w.])fetch\s*\(/.test(code))imports.push('officialFetch as fetch');
   if(/new\s+WebSocket\s*\(/.test(code))imports.push('OfficialWebSocket as WebSocket');
   if(imports.length)code=`import {${imports.join(',')}} from 'hermes-platform-transport';\n`+code;
   if(path.endsWith('/themes/context.tsx'))code=code.replaceAll('document.documentElement',"(document.querySelector<HTMLElement>('.hermes-official') ?? document.documentElement)");
   return {code,map:null};
  },
 };
}
