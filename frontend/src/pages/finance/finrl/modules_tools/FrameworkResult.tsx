import {apiUrl} from '../../../../data/api';
import {DataTable} from '../../../../ui/DataTable';
import type {Job} from '../../../../data/types';
export function FrameworkResult({job}:{job:Job}){
 const result=job.result as {value?:{columns?:string[];rows?:Record<string,unknown>[];total_rows?:number};figures?:string[]}|undefined,value=result?.value;
 return <div className="mt-3 space-y-4">{value?.columns&&value.rows&&<><p className="text-xs text-slate-500">실제 전체 {value.total_rows??value.rows.length}행 · 표시 {value.rows.length}행</p><DataTable<Record<string,unknown>> items={value.rows} label="공식 실행 결과" keyFor={row=>String(value.rows?.indexOf(row))} columns={value.columns.map(key=>({key,label:key,render:row=>typeof row[key]==='object'?JSON.stringify(row[key]):String(row[key]??'')}))}/></>}
 {result?.figures?.map(name=><img key={name} src={apiUrl('framework/artifact/'+job.id+'/'+name)} alt="공식 모듈이 생성한 실제 결과 그래프" className="w-full rounded-xl bg-white"/>)}
 <details open={!value?.rows}><summary className="cursor-pointer text-xs text-slate-500">원본 결과·오류·로그</summary><pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-all text-xs">{job.result?JSON.stringify(job.result,null,2):job.log_text}</pre></details>
 {job.status==='succeeded'&&<a className="block text-xs text-blue-600" href={apiUrl('framework/result/'+job.id)} download>전체 결과 JSON 다운로드</a>}
 </div>;
}
