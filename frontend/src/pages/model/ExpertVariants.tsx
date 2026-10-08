import type {LibraryExpert} from '../../data/library';
import {bytes,number} from '../../ui/format';
export function ExpertVariants({variants,selected,active,onSelect}:{variants:LibraryExpert[];selected:string;active:string[];onSelect:(id:string)=>void}){
 return <div className="flex min-w-0 flex-wrap gap-2" role="group" aria-label="Expert 정밀도 버전">
  {variants.map(v=>{const comparison=v.conversion?.comparison as {speed_ratio?:number}|undefined;return <button key={v.id} aria-pressed={selected===v.id} onClick={e=>{e.stopPropagation();onSelect(v.id)}} className={`min-w-20 rounded-xl px-3 py-2 text-left text-xs transition active:scale-95 focus-visible:outline-2 focus-visible:outline-blue-500 ${selected===v.id?'bg-blue-50 ring-1 ring-blue-300':'bg-slate-50 hover:bg-slate-100'}`}>
   <span className={`block font-semibold ${active.includes(v.id)?'text-emerald-700':'text-slate-700'}`}>{v.conversion?.precision.toUpperCase()??v.representation?.split(' · ')[0]??'원본'}{active.includes(v.id)?' · 사용':''}</span>
   <span className="mt-1 block text-slate-400">{bytes(v.package.bytes)}</span>
   {v.conversion?.validation&&<span className={`mt-1 block ${v.conversion.validation.passed?'text-emerald-600':'text-amber-700'}`}>오차 {number(v.conversion.validation.relative_rmse*100,3)}%{v.conversion.validation.passed?'':' · 기준 초과'}</span>}
   {comparison?.speed_ratio!=null&&<span className="mt-1 block text-slate-500">속도 {number(comparison.speed_ratio,2)}배</span>}
  </button>})}
 </div>;
}
