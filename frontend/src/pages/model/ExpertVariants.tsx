import {useState} from 'react';
import type {LibraryExpert,Optimization} from '../../data/library';
import {Drawer} from '../../ui/Primitives';
import {bytes,number,inspectionDetail,date,percent} from '../../ui/format';
export function ExpertVariants({variants,quantization,legacyFailures,selectedIds,selectedFailurePrecisions,onToggle,onToggleFailure}:{variants:LibraryExpert[];quantization?:Optimization;legacyFailures?:Optimization;selectedIds:string[];selectedFailurePrecisions:string[];onToggle:(id:string)=>void;onToggleFailure:(precision:string)=>void}){
 const [detailId,setDetailId]=useState<string|null>(null),detail=variants.find(item=>item.id===detailId);
 const failures=new Map<string,{reason:string;finished?:number}>();
 for(const record of [legacyFailures,quantization]){
  for(const row of record?.reports??[])if(row.precision&&['created','existing'].includes(row.status??''))failures.delete(row.precision);
  for(const row of record?.failures??[])if(!variants.some(item=>item.package_available&&item.conversion?.precision===row.precision))failures.set(row.precision,{reason:row.detail,finished:record?.finished});
 }
 const detailReport=detail?(quantization?.reports?.find(row=>row.id===detail.id)??legacyFailures?.reports?.find(row=>row.id===detail.id)):undefined;
 const comparison=detail?.conversion?.comparison as {relative_rmse?:number;action_agreement?:number|null;direction_agreement?:number|null;input_as_of?:string;input_sha256?:string}|undefined;
 const quality=detail?.conversion?.validation??comparison??detailReport;
 const ratio=(value:number|null|undefined)=>value==null||!Number.isFinite(value)?'미측정':percent(value);
 return <div className="min-w-0">
  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 2xl:grid-cols-5" role="group" aria-label="Champion 조립용 모델 버전">
   {variants.map(item=>{const selected=selectedIds.includes(item.id),conversion=item.conversion,report=quantization?.reports?.find(row=>row.id===item.id);const failed=!item.package_available||!!item.metadata_error;const precision=conversion?.precision?.toUpperCase()??item.representation??'정밀도 미확인',bits=/^(INT4|NF4)/.test(precision)?'4비트':/^INT8/.test(precision)?'8비트':/^(FP16|BF16)/.test(precision)?'16비트':/^FP32/.test(precision)?'32비트':null;const label=item.executor==='llama_cpp'?item.representation??'GGUF 정밀도 미확인':precision+(bits?' · '+bits:'');return <div key={item.id} className={'min-w-0 rounded-xl p-2.5 text-xs '+(selected?'bg-blue-50 ring-1 ring-blue-300':failed?'bg-amber-50':'bg-slate-50')}>
    <label className="mb-2 flex cursor-pointer items-center gap-2 text-slate-500"><input type="checkbox" checked={selected} onChange={()=>onToggle(item.id)} aria-label={item.name+' '+label+' 선택'}/>선택</label>
    <button aria-label={item.name+' '+label+' 상세·검사 결과'} onClick={()=>setDetailId(item.id)} className="w-full text-left focus-visible:outline-2 focus-visible:outline-blue-500">
     <b className="block break-words text-slate-700">{label}</b><span className="mt-1 block text-slate-500">{bytes(item.weight_bytes??item.package.bytes)}</span>
     <span className={'mt-2 block '+(failed?'text-rose-700':'text-emerald-700')}>{failed?'가중치·정밀도 확인 실패':item.quantized||conversion?.precision?.match(/^(int8|int4|nf4)$/)?'양자화 가중치':conversion?'비양자화 · 정밀도 변환':'비양자화 · 원본'}</span>
     {failed&&<span className="mt-1 block break-words text-rose-700">{inspectionDetail(item.metadata_error??'등록된 패키지 파일이 없거나 크기가 다릅니다.')}</span>}
     {conversion?.validation&&<span className="mt-1 block text-slate-500">판단 일치 {ratio(conversion.validation.action_agreement)} · 방향 일치 {ratio(conversion.validation.direction_agreement)}</span>}
     {conversion?.original_tensor_bytes!=null&&<span className="mt-2 block text-slate-500">가중치 {bytes(conversion.original_tensor_bytes)} → {bytes(conversion.converted_tensor_bytes)}</span>}
     {!!conversion?.layers&&<span className="mt-1 block text-slate-500">양자화 계층 {number(conversion.layers,0)}개</span>}
     {report?.seconds!=null&&<span className="mt-1 block text-slate-500">처리 {number(report.seconds,2)}s</span>}
     <span className="mt-2 block text-blue-600 underline">상세·검사 결과</span>
    </button>
   </div>})}
  </div>
  {!!failures.size&&<div className="mt-2 space-y-1">{[...failures].map(([precision,{reason,finished}])=><label key={precision} className="flex cursor-pointer items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800"><input type="checkbox" checked={selectedFailurePrecisions.includes(precision)} onChange={()=>onToggleFailure(precision)} aria-label={precision+' 실패 기록 선택'}/><span>과거 {precision.toUpperCase()} 변환 시도 실패 · {date(finished)} · {inspectionDetail(reason)}</span></label>)}</div>}
  <Drawer title={detail?.name+' · 정밀도·검사 결과'} open={!!detail} onClose={()=>setDetailId(null)}>{detail&&<div className="space-y-4 text-sm">
   <p className="font-semibold">{detail.representation??detail.conversion?.precision?.toUpperCase()??'정밀도 미확인'} · {detail.quantized?'양자화 가중치':'비양자화 가중치'}</p>
   <p>가중치 크기 {bytes(detail.weight_bytes??detail.package.bytes)} · 출력 {detail.feature_size}D · 실제 파라미터 {number(detail.parameters,0)}개</p>
   {detail.metadata_error&&<p className="text-rose-700">{inspectionDetail(detail.metadata_error)}</p>}
   <div className="rounded-xl bg-slate-50 p-3"><b>저장된 원본 출력 비교</b><dl className="mt-2 grid grid-cols-2 gap-2"><dt>판단 일치도</dt><dd>{ratio(quality?.action_agreement)}</dd><dt>예측 방향 일치도</dt><dd>{ratio(quality?.direction_agreement)}</dd><dt>상대 RMSE</dt><dd>{ratio(quality?.relative_rmse)}</dd></dl><p className="mt-2 text-xs text-slate-500">미측정은 기록이 없거나 해당 출력에 적용되지 않는 항목입니다. 양자화 여부와 원본 출력의 일치도는 별개입니다.</p>{detail.conversion?.validation&&<p className="mt-2">저장된 비교 기준 {detail.conversion.validation.passed==null?'미확인':detail.conversion.validation.passed?'통과':'미충족'} · 상대 RMSE 허용치 {ratio(detail.conversion.validation.max_relative_rmse)} · 일치도 기준 {ratio(detail.conversion.validation.min_action_agreement)}</p>}{comparison?.input_as_of&&<p className="mt-2 text-xs">비교 입력 시점 {comparison.input_as_of}</p>}</div>
   <p>저장된 추론 검사: {detail.check?.status??'미검사'} · {inspectionDetail(detail.check?.detail??'검사 기록 없음')}</p>
   {detail.check?.tested&&<p className="text-xs text-slate-500">검사 시점 {date(detail.check.tested)}</p>}
   {detailReport?.detail&&<p>변환 기록: {inspectionDetail(detailReport.detail)}</p>}
   <p className="break-all text-xs text-slate-500">{detail.package_path}</p>
  </div>}</Drawer>
 </div>;
}
