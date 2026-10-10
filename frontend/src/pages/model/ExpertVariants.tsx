import type {LibraryExpert,Optimization} from '../../data/library';
import {bytes,number,inspectionDetail} from '../../ui/format';
export function ExpertVariants({variants,quantization,legacyFailures,selectedIds,selectedFailurePrecisions,onToggle,onToggleFailure}:{variants:LibraryExpert[];quantization?:Optimization;legacyFailures?:Optimization;selectedIds:string[];selectedFailurePrecisions:string[];onToggle:(id:string)=>void;onToggleFailure:(precision:string)=>void}){
 const failures=new Map<string,string>();
 for(const record of [legacyFailures,quantization])for(const row of record?.failures??[])if(!variants.some(item=>item.conversion?.precision===row.precision))failures.set(row.precision,row.detail);
 return <div className="min-w-0">
  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 2xl:grid-cols-5" role="group" aria-label="Champion 조립용 모델 버전">
   {variants.map(item=>{const selected=selectedIds.includes(item.id),conversion=item.conversion,report=quantization?.reports?.find(row=>row.id===item.id);const failed=report?.status==='failed'||!item.package_available;const label=item.executor==='llama_cpp'?item.representation??'GGUF 정밀도 미확인':conversion?.precision?.toUpperCase()??item.representation??'원본';return <div key={item.id} className={'min-w-0 rounded-xl p-2.5 text-xs '+(selected?'bg-blue-50 ring-1 ring-blue-300':failed?'bg-amber-50':'bg-slate-50')}>
    <label className="mb-2 flex cursor-pointer items-center gap-2 text-slate-500"><input type="checkbox" checked={selected} onChange={()=>onToggle(item.id)} aria-label={item.name+' '+label+' 선택'}/>선택</label>
    <button aria-pressed={selected} onClick={()=>onToggle(item.id)} className="w-full text-left focus-visible:outline-2 focus-visible:outline-blue-500">
     <b className="block break-words text-slate-700">{label}</b><span className="mt-1 block text-slate-500">{bytes(item.weight_bytes??item.package.bytes)}</span>
     <span className={'mt-2 block '+(failed?'text-rose-700':'text-emerald-700')}>{failed?'가중치 파일 확인 실패':item.quantized||conversion?.precision?.match(/^(int8|int4|nf4)$/)?'양자화 완료':conversion?'변환 완료':'원본'}</span>
     {failed&&<span className="mt-1 block break-words text-rose-700">{inspectionDetail(report?.detail??'등록된 패키지 파일이 없거나 크기가 다릅니다.')}</span>}
     {conversion?.original_tensor_bytes!=null&&<span className="mt-2 block text-slate-500">가중치 {bytes(conversion.original_tensor_bytes)} → {bytes(conversion.converted_tensor_bytes)}</span>}
     {!!conversion?.layers&&<span className="mt-1 block text-slate-500">양자화 계층 {number(conversion.layers,0)}개</span>}
     {report?.seconds!=null&&<span className="mt-1 block text-slate-500">처리 {number(report.seconds,2)}s</span>}
    </button>
   </div>})}
  </div>
  {!!failures.size&&<div className="mt-2 space-y-1">{[...failures].map(([precision,reason])=><label key={precision} className="flex cursor-pointer items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800"><input type="checkbox" checked={selectedFailurePrecisions.includes(precision)} onChange={()=>onToggleFailure(precision)} aria-label={precision+' 실패 기록 선택'}/><span>{precision.toUpperCase()} 양자화 실패 · {inspectionDetail(reason)}</span></label>)}</div>}
 </div>;
}
