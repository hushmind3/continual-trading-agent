import {DocumentLink,documentPath} from './DocumentLink';

export function GeneratedFiles({steps}:{steps:{name:string;args:string;result?:unknown}[]}){
 const files=new Set<string>();
 for(const step of steps){
  if(!['write_file','patch'].includes(step.name)||step.result===undefined)continue;
  try{const result=typeof step.result==='string'?JSON.parse(step.result):step.result;if(result&&typeof result==='object'&&('error' in result||('success' in result&&result.success===false)))continue;const args=JSON.parse(step.args);if(typeof args.path==='string'){const path=documentPath(args.path);if(path)files.add(path)}}catch{/* Unverified output does not become an attachment. */}
 }
 return files.size?<div className="flex flex-wrap items-center gap-2" aria-label="결과 파일"><span>결과 파일</span>{[...files].map(path=><DocumentLink key={path} path={path}>{path.split(/[\\/]/).at(-1)}</DocumentLink>)}</div>:null;
}
