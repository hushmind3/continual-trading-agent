import {listPackage,statFile,extractFile} from '@electron/asar';
import {mkdirSync,writeFileSync} from 'node:fs';
import {resolve,relative,isAbsolute,dirname} from 'node:path';
const [archive,output]=process.argv.slice(2),root=resolve(output),missing=[];
mkdirSync(root,{recursive:true});
for(const entry of listPackage(archive)){
 const name=entry.replace(/^[/\\]+/,'');
 const path=resolve(root,name),rel=relative(root,path);
 if(rel.startsWith('..')||isAbsolute(rel))throw Error('Archive path escapes output: '+entry);
 const info=statFile(archive,name,false);
 if(info.files)continue;
 if(info.link){missing.push({path:name,reason:'archive link',target:info.link});continue;}
 try{const bytes=extractFile(archive,name);mkdirSync(dirname(path),{recursive:true});writeFileSync(path,bytes,{flag:'wx'});}
 catch(error){missing.push({path:name,reason:String(error.message)});}
}
process.stdout.write(JSON.stringify({unavailable:missing}));
