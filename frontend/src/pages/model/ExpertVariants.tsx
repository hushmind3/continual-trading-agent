import {useState} from 'react';
import type {LibraryExpert,Optimization,Inspection} from '../../data/library';
import {bytes,number,inferenceChange,inspectionDetail} from '../../ui/format';
import {versionResults} from './expertVersionResults';
import {ExpertVersionEvidence} from './ExpertVersionEvidence';
export function ExpertVariants({base,variants,selected,active,optimization,inspection,onSelect}:{base:LibraryExpert;variants:LibraryExpert[];selected:string;active:string[];optimization?:Optimization;inspection?:Inspection;onSelect:(id:string)=>void}){
 const [evidence,setEvidence]=useState('');
 const results=versionResults(base,variants,selected,active,optimization,inspection);
 const detail=results.find(r=>r.key===evidence);
 return <div className="min-w-0" onClick={e=>e.stopPropagation()}>
  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 2xl:grid-cols-5" role="group" aria-label="Expert 정밀도 버전">
   {results.map(v=>{const item=v.item;const comparison=item?.conversion?.comparison as {speed_ratio?:number}|undefined;const failed=['failed','rejected'].includes(v.inspection.status)||['failed','rejected'].includes(v.decision.status);return <div key={v.key} className={`min-w-0 rounded-xl p-2.5 text-xs ${item?.id===selected?'bg-blue-50 ring-1 ring-blue-300':failed?'bg-amber-50/70':item?'bg-slate-50':'bg-slate-50/50 ring-1 ring-inset ring-slate-100'}`}>
    <button aria-pressed={item?.id===selected} onClick={()=>item?onSelect(item.id):setEvidence(v.key)} className="w-full text-left transition active:scale-95 focus-visible:rounded focus-visible:outline-2 focus-visible:outline-blue-500">
     <span className={`block font-semibold ${item&&active.includes(item.id)?'text-emerald-700':'text-slate-700'}`}>{v.label}{item&&active.includes(item.id)?' · 사용':''}</span>
     {(item||v.report?.bytes!=null)&&<span className="mt-1 block text-slate-400">{bytes(item?.package.bytes??v.report?.bytes)}</span>}
     <span className={`mt-2 block ${v.inspection.status==='passed'?'text-emerald-700':failed?'text-amber-800':'text-slate-500'}`}>{v.inspection.label}</span>
     {['failed','rejected'].includes(v.inspection.status)&&<span className="mt-1 line-clamp-3 block break-words text-[11px] leading-4 text-amber-800" title={inspectionDetail(v.inspection.detail)}>{inspectionDetail(v.inspection.detail)}</span>}
     {item?.conversion?.validation&&<span className="mt-1 block text-slate-500">오차 {number(item.conversion.validation.relative_rmse*100,3)}%</span>}
     {comparison?.speed_ratio!=null&&<span className="mt-1 block text-slate-500">{inferenceChange(comparison.speed_ratio)}</span>}
    </button>
    <p className={`mt-2 text-xs ${v.decision.status==='selected'?'font-semibold text-blue-700':failed?'text-amber-800':'text-slate-500'}`}>{v.decision.label}</p>
    {v.decision.status!=='pending'&&<p className="mt-1 line-clamp-3 break-words text-[11px] leading-4 text-slate-500" title={v.decision.detail}>{v.decision.detail}</p>}
    <button className="mt-2 rounded py-1 text-xs text-blue-700 underline decoration-blue-200 underline-offset-2 hover:text-blue-900 focus-visible:outline-2 focus-visible:outline-blue-500" onClick={()=>setEvidence(v.key)}>판단 근거</button>
   </div>})}
  </div>
  <p className="mt-2 text-[11px] text-slate-400">현재 검사와 마지막 최적화 판단은 별도 표시 · 미생성·탈락·정리된 버전도 포함</p>
  {detail&&<ExpertVersionEvidence name={base.name} result={detail} optimization={optimization} onSelect={onSelect} onClose={()=>setEvidence('')}/>}
 </div>;
}
