import {LockKeyhole} from 'lucide-react';
import type {Expert} from '../../data/types';
import {Drawer,Empty} from '../../ui/Primitives';
import {bytes,date,number} from '../../ui/format';
export function ExpertInspector({expert,close}:{expert:Expert|null;close:()=>void}){
 const inference=expert?.inference;
 return <Drawer title={expert?.name??'Expert'} open={Boolean(expert)} onClose={close}>
  {expert&&<div className="space-y-6">
   <div className="rounded-2xl bg-violet-50 p-5"><div className="flex items-center gap-2 text-sm font-semibold text-violet-700"><LockKeyhole size={16}/>Frozen Expert · 고정 가중치</div><p className="mt-2 text-sm leading-6 text-violet-700/70">현재 SAC 시스템에서 Expert는 고정된 입력 분석기입니다. 중앙 MoE 정책 학습은 제공되지 않습니다.</p></div>
   {expert.input.reason&&<p className="text-sm text-amber-700">입력 연결 상태: {expert.input.reason}</p>}
   <dl className="grid grid-cols-2 gap-x-4 gap-y-5 text-sm">
    <Detail label="모델 파일" value={expert.package_available?'사용 가능':'파일 없음'}/><Detail label="적재 상태" value={expert.loaded?'적재 중':'미적재'}/>
    <Detail label="파라미터" value={number(expert.parameters,0)}/><Detail label="장치" value={String(expert.current_resources?.device??expert.resources?.device??'미확인')}/>
    <Detail label="RAM" value={bytes(Number(expert.current_resources?.ram_bytes??expert.resources?.ram_bytes??0))}/><Detail label="VRAM" value={bytes(Number(expert.current_resources?.vram_bytes??expert.resources?.vram_bytes??0))}/>
    <Detail label="최근 입력 시각" value={date(inference?.as_of)}/><Detail label="추론 상태" value={inference?.status??'기록 없음'}/>
   </dl>
   <section className="space-y-2"><h3 className="text-sm font-semibold">입력 계약</h3><p className="text-xs leading-5 text-slate-500">{expert.input.requires?.join(' · ')??expert.input.reason??'입력 정보 없음'}</p>{(expert.input.universe?.length??0)>0&&<p className="text-xs text-slate-500">종목: {(expert.input.universe??[]).join(' · ')}</p>}</section>
   <details className="border-t border-slate-100 pt-4"><summary className="cursor-pointer text-sm font-medium text-slate-500">실제 추론 결과 · 진단</summary>{inference?.reason&&<p className="mt-3 text-xs text-amber-700">{inference.reason}</p>}{inference?.output?<pre className="mt-3 max-h-96 overflow-auto rounded-xl bg-slate-950 p-4 text-[11px] leading-5 text-slate-300">{JSON.stringify(inference.output,null,2)}</pre>:<Empty title="저장된 실제 출력이 없습니다."/>}<p className="mt-2 font-mono text-xs text-slate-400">{expert.id}</p></details>
  </div>}
 </Drawer>;
}
function Detail({label,value}:{label:string;value:string}){return <div><dt className="mb-1 text-xs text-slate-400">{label}</dt><dd className="font-medium tabular-nums">{value}</dd></div>}
