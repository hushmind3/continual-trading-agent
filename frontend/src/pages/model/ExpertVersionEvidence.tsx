import type {Optimization} from '../../data/library';
import {Button,Drawer} from '../../ui/Primitives';
import {bytes,date,number,percent,inspectionDetail} from '../../ui/format';
import type {VersionResult} from './expertVersionResults';

export function ExpertVersionEvidence({name,result,optimization,onSelect,onClose}:{name:string;result:VersionResult;optimization?:Optimization;onSelect:(id:string)=>void;onClose:()=>void}){
 const r=result.report,m=r?.measurement;
 return <Drawer title={`${name} · ${result.label} 판단 근거`} open onClose={onClose}>
  <div className="space-y-5 text-sm">
   <section className="space-y-2 rounded-xl bg-slate-50 p-4"><h3 className="font-semibold">현재 검사 · {result.inspection.label}</h3><p className="break-words text-xs leading-6 text-slate-600">{inspectionDetail(result.inspection.detail)}</p>{result.item?.check.tested&&<p className="text-xs text-slate-400">검사 시각 {date(result.item.check.tested)}</p>}</section>
   <section className="space-y-2 rounded-xl bg-blue-50 p-4"><h3 className="font-semibold">자동 최적화 · {result.decision.label}</h3><p className="break-words text-xs leading-6 text-slate-600">{result.decision.detail}</p>{optimization&&<p className="text-xs text-slate-500">목표: {optimization.goal==='speed'?'속도':optimization.goal==='memory'?'메모리':'속도 60% · 메모리 40%'} · {date(optimization.finished??optimization.started)}<br/>선택 {optimization.selected??'판단 중'} · 이전 {optimization.previous??'기록 없음'}<br/>같은 입력 {date(optimization.input_as_of)}{r?.score!=null?` · 목표 점수 ${number(r.score,3)} (낮을수록 유리)`:''}</p>}</section>
   {r&&<p className="break-all text-xs text-slate-500">최적화 측정 대상: {r.id}</p>}
   {m&&<dl className="grid grid-cols-2 gap-4 text-xs">
    {[['측정 파일 크기',bytes(r?.bytes)],['반복 추론 중앙값',m.warm_median_seconds!=null?number(m.warm_median_seconds,4)+'s':'미측정'],['peak RAM',bytes(m.metrics?.peak_ram_bytes)],['peak VRAM',bytes(m.metrics?.peak_vram_bytes)],['실행 장치',m.metrics?.device??'미측정'],['원본 대비 오차',r?.relative_rmse!=null?percent(r.relative_rmse,3):'원본 기준'],['판단 일치',r?.action_agreement!=null?percent(r.action_agreement):'해당 없음'],['예측 방향 일치',r?.direction_agreement!=null?percent(r.direction_agreement):'해당 없음']].map(([label,value])=><div key={label}><dt className="text-slate-400">{label}</dt><dd className="mt-1 break-words font-semibold">{value}</dd></div>)}
   </dl>}
   {!result.item&&result.inspection.status!=='native'&&<p className="text-xs leading-6 text-slate-500">현재 사용할 가중치 파일이 없습니다. 탈락 사유와 측정 결과를 보여주는 항목이며, 존재하지 않는 패키지를 사용 구성에 넣지 않습니다.</p>}
   {result.versions.length>0&&<section className="space-y-3"><h3 className="text-xs font-semibold">보관 중인 이 정밀도의 패키지</h3>{result.versions.map(v=><div key={v.id} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 p-3"><div className="min-w-0 text-xs"><p className="break-all font-semibold">{v.id}</p><p className="mt-1 text-slate-500">{bytes(v.package.bytes)} · {inspectionDetail(v.check.detail)}</p></div><Button onClick={()=>{onSelect(v.id);onClose()}}>버전 보기</Button></div>)}</section>}
  </div>
 </Drawer>;
}
