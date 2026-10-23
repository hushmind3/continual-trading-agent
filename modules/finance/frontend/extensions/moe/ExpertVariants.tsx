import {useState,useCallback} from 'react';
import type {LibraryExpert,Optimization,OptimizationReport} from '@platform/data/library';
import {Drawer,Input,Button} from '@platform/ui/Primitives';
import {bytes,number,inspectionDetail,date,percent} from '@platform/ui/format';
export function ExpertVariants({disabled=false,variants,quantization,legacyFailures,selectedIds,selectedFailurePrecisions,onToggle,onToggleFailure}:{disabled?:boolean;variants:LibraryExpert[];quantization?:Optimization;legacyFailures?:Optimization;selectedIds:string[];selectedFailurePrecisions:string[];onToggle:(id:string)=>void;onToggleFailure:(precision:string)=>void}){
 const [detailId,setDetailId]=useState<string|null>(null),detail=variants.find(item=>item.id===detailId);
 const closeDetail=useCallback(()=>setDetailId(null),[]);
 const failures=new Map<string,{reason:string;finished?:number}>();
 for(const record of [legacyFailures,quantization]){
  for(const row of record?.reports??[])if(row.precision&&['created','existing'].includes(row.status??''))failures.delete(row.precision);
  for(const row of record?.failures??[])if(!variants.some(item=>item.package_available&&item.conversion?.precision===row.precision))failures.set(row.precision,{reason:row.detail,finished:record?.finished});
 }
 const detailReport=detail?(quantization?.reports?.find(row=>row.id===detail.id)??legacyFailures?.reports?.find(row=>row.id===detail.id)):undefined;
 const comparison=detail?.conversion?.comparison as OptimizationReport|undefined;
 const quality=detailReport?.comparison_status?detailReport:comparison??detail?.conversion?.validation??detailReport;
 const ratio=(value:number|null|undefined)=>value==null||!Number.isFinite(value)?'미측정':percent(value);
 return <div className="min-w-0">
  <div className="flex flex-wrap gap-2" role="group" aria-label="Champion 조립용 모델 버전">
   {variants.map(item=>{const selected=selectedIds.includes(item.id),conversion=item.conversion;const failed=!item.package_available||!!item.metadata_error;const precision=conversion?.precision?.toUpperCase()??item.representation??'정밀도 미확인',bits=/^(INT4|NF4)/.test(precision)?'4비트':/^INT8/.test(precision)?'8비트':/^(FP16|BF16)/.test(precision)?'16비트':/^FP32/.test(precision)?'32비트':null;const label=item.executor==='repository_source'?'원본 등록':item.executor==='llama_cpp'?item.representation??'GGUF':precision+(bits?' · '+bits:'');return <div key={item.id} className={'expert-version '+(selected?'expert-version-selected ':failed?'expert-version-warning ':'')}>
    <label className="expert-version-selection"><Input type="checkbox" disabled={disabled} checked={selected} onChange={()=>onToggle(item.id)} aria-label={(item.name||item.id)+' '+label+' 선택'}/><span>{label}</span></label>
    <Button aria-label={(item.name||item.id)+' '+label+' 상세·검사 결과'} onClick={()=>setDetailId(item.id)} className="expert-version-detail">
     <span className="expert-version-size">{item.package_available?bytes(item.weight_bytes??item.package.bytes):'파일 없음 · 크기 미확인'}</span>
     {item.loaded&&<span className="expert-version-meta">로드됨{typeof item.current_resources?.device==='string'?' · '+item.current_resources.device:''}</span>}
     <span className={'expert-version-state '+(failed?'text-rose-700':'text-slate-500')}>{failed?'등록 파일 확인 필요':item.executor==='repository_source'?'입력·실행기 미설정':item.quantized||conversion?.precision?.match(/^(int8|int4|nf4)$/)?'양자화 가중치':conversion?'정밀도 변환':precision==='정밀도 미확인'?'정밀도 정보 미기재':'원본 가중치'}</span>
     <span className="expert-version-link">상세 보기 <span aria-hidden="true">↗</span></span>
    </Button>
   </div>})}
  </div>
  {!!failures.size&&<details className="expert-failure-records"><summary>변환 실패 기록 {failures.size}개</summary><div className="mt-2 space-y-1">{[...failures].map(([precision,{reason,finished}])=><label key={precision} className="flex cursor-pointer items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800"><Input type="checkbox" disabled={disabled} checked={selectedFailurePrecisions.includes(precision)} onChange={()=>onToggleFailure(precision)} aria-label={precision+' 실패 기록 선택'}/><span>과거 {precision.toUpperCase()} 변환 시도 실패 · {date(finished)} · {inspectionDetail(reason)}</span></label>)}</div></details>}
  <Drawer title={detail?.name+' · 정밀도·검사 결과'} open={!!detail} onClose={closeDetail}>{detail&&<div className="space-y-4 text-sm">
   <p className="font-semibold">{detail.representation??detail.conversion?.precision?.toUpperCase()??'정밀도 미확인'} · {detail.quantized?'양자화 가중치':'비양자화 가중치'}</p>
   <p>가중치 크기 {bytes(detail.weight_bytes??detail.package.bytes)} · 출력 {detail.feature_size}D · 실제 파라미터 {number(detail.parameters,0)}개</p>
   {(detail.metadata_error||!detail.package_available)&&<p className="text-rose-700">{inspectionDetail(detail.metadata_error??'등록된 패키지 파일이 없거나 크기가 다릅니다.')}</p>}
   <div className="rounded-xl bg-slate-50 p-3"><b>저장된 원본 출력 비교</b><dl className="mt-2 grid grid-cols-2 gap-2"><dt>판단 일치도</dt><dd>{detail.role==='action'?ratio(quality?.action_agreement):'해당 없음 · 매매 행동 출력이 아님'}</dd><dt>예측 방향 일치도</dt><dd>{detail.role==='market'?ratio(quality?.direction_agreement):'해당 없음 · 매매 행동 모델'}</dd><dt>상대 RMSE</dt><dd>{ratio(quality?.relative_rmse)}</dd><dt>RMSE</dt><dd>{number(detailReport?.comparison_status?detailReport.rmse:comparison?.rmse,6)}</dd><dt>평균 절대 오차</dt><dd>{number(detailReport?.comparison_status?detailReport.mean_absolute_error:comparison?.mean_absolute_error,6)}</dd><dt>최대 절대 오차</dt><dd>{number(detailReport?.comparison_status?detailReport.max_absolute_error:comparison?.max_absolute_error,6)}</dd></dl>{detailReport?.comparison_error&&<p className="mt-2 text-amber-800">원본 비교 {detailReport.comparison_status==='failed'?'실패':'불가'} · {inspectionDetail(detailReport.comparison_error)}</p>}<p className="mt-2 text-xs text-slate-500">동일한 실제 입력에 대한 원본 출력 차이입니다. 매매 수익률·미래 예측 정확도 측정은 아닙니다. 비교 기록이 없거나 비교에 실패한 값은 미측정입니다.</p>{detail.conversion?.validation&&<p className="mt-2">과거 비교 기준 {detail.conversion.validation.passed==null?'미확인':detail.conversion.validation.passed?'통과':'미충족'} · 상대 RMSE 허용치 {ratio(detail.conversion.validation.max_relative_rmse)} · 일치도 기준 {ratio(detail.conversion.validation.min_action_agreement)}</p>}{(detailReport?.input_as_of??comparison?.input_as_of)&&<p className="mt-2 text-xs">비교 입력 시점 {detailReport?.input_as_of??comparison?.input_as_of}</p>}</div>
   <p>저장된 추론 검사: {detail.check?.status??'미검사'} · {inspectionDetail(detail.check?.detail??'검사 기록 없음')}</p>
   {detail.check?.tested&&<p className="text-xs text-slate-500">검사 시점 {date(detail.check.tested)}</p>}
   {detail.conversion?.original_tensor_bytes!=null&&<p>가중치 변환 {bytes(detail.conversion.original_tensor_bytes)} → {bytes(detail.conversion.converted_tensor_bytes)}</p>}
   {!!detail.conversion?.layers&&<p>양자화 계층 {number(detail.conversion.layers,0)}개</p>}
   {detailReport?.seconds!=null&&<p>변환 처리 {number(detailReport.seconds,2)}s</p>}
   {detailReport?.detail&&<p>변환 기록: {inspectionDetail(detailReport.detail)}</p>}
   <p className="break-all text-xs text-slate-500">{detail.package_path}</p>
  </div>}</Drawer>
 </div>;
}
