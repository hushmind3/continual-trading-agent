import {useOperations} from '../../data/Operations';
import {Panel} from '../../ui/Panel';
import {Empty,Status} from '../../ui/Primitives';
import {bytes,date,number} from '../../ui/format';
import {Capability} from '../../ui/Capability';
import {useState} from 'react';
import {Button,ErrorMessage} from '../../ui/Primitives';
import {inputClass} from '../../ui/Primitives';
import {useEndpoint} from '../../data/useEndpoint';
import type {Champion} from '../../data/library';
import type {Currency} from '../../data/types';
import {ChampionSpec} from '../../ui/ChampionSpec';
export function CheckpointPanel({operating=false}:{operating?:boolean}){const {state:s,execute,pending}=useOperations();const [error,setError]=useState(''),[message,setMessage]=useState(''),[currency,setCurrency]=useState<Currency>('USD'),[path,setPath]=useState('');const champions=useEndpoint<{items:Champion[]}>(operating?'champions':null);if(!s)return null;
 if(operating){const selected=s.operations?.policies?.[currency],options=s.checkpoints.filter(c=>c.identity.currency===currency),chosenPath=options.some(c=>c.path===path)?path:selected?.path??'',chosen=options.find(c=>c.path===chosenPath),model=champions.data?.items.find(c=>c.checkpoint===chosenPath);
  return <Panel title="운영 모델 선택 · 로딩" description="선택한 FinRL 정책·SAC Champion의 중앙 정책을 실제 로드합니다. Expert는 추론 시 모델에 저장된 구성으로 사용합니다.">
   <div className="flex flex-wrap items-center gap-3"><select aria-label="운영 모델 통화" className={inputClass+' !w-auto'} value={currency} onChange={e=>{setCurrency(e.target.value as Currency);setPath('');setMessage('');setError('')}}><option value="USD">USD</option><option value="KRW">KRW</option></select><select aria-label="운영 FinRL 모델 선택" className={inputClass+' min-w-64 !w-auto flex-1'} value={chosenPath} onChange={e=>{setPath(e.target.value);setMessage('');setError('')}}><option value="">운영 모델 선택</option>{options.map(c=><option key={c.path} value={c.path}>{c.name} · {String(c.identity.algorithm??'').toUpperCase()} · {c.num_timesteps===0?'미학습':number(c.num_timesteps,0)+'단계'}</option>)}</select><Button tone="primary" disabled={!chosen||s.job.running} busy={pending.has('checkpoints/restore')} onClick={async()=>{setError('');try{const r=await execute<{message:string}>('checkpoints/restore',{path:chosenPath});setMessage(r.message)}catch(e){setError(e instanceof Error?e.message:'모델 로딩 실패')}}}>선택 모델 로드</Button></div>
   {!options.length&&<p className="mt-3 text-xs text-amber-700">{currency}의 FinRL 체크포인트가 없습니다.</p>}
   <div className="mt-3"><Status tone={selected?.loaded?'good':'idle'}>{selected?.loaded?'중앙 정책 로드됨 · '+selected.device:selected?.path?'운영 모델 선택됨 · 중앙 정책 미로드':'운영 모델 미선택'}</Status>{selected?.path&&<p className="mt-2 break-all text-xs text-slate-500">현재 운영: {selected.path}{selected.loaded?' · 관측 '+selected.observation_shape?.join(' × ')+' · 행동 '+selected.action_shape?.join(' × '):''}</p>}</div>
   <ErrorMessage message={error||champions.error}/>{message&&<p className="mt-3 text-xs text-emerald-700">{message}</p>}
   {model&&<div className="mt-4 rounded-xl bg-slate-50 p-4"><ChampionSpec model={model}/></div>}
   {chosen&&!model&&<p className="mt-3 text-xs text-slate-500">{chosen.identity.currency as string} · {(chosen.identity.symbols as string[]|undefined)?.length??0}종목 · 정책 {bytes(chosen.file.bytes)} · {number(chosen.num_timesteps,0)}단계 / {number(chosen.updates,0)} 업데이트</p>}
  </Panel>
 }
 return <Panel title="저장 정책 · 체크포인트" description="현재 FinRL 정책과 보관된 실제 파일 · 원본 경로는 종료 시 저장">
 {s.checkpoints.length?s.checkpoints.map(c=><div key={c.path} className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 py-4"><div><b className="text-sm">{c.name} · {String(c.identity.algorithm??'').toUpperCase()}</b><p className="mt-1 text-xs text-slate-400">{date(c.file.modified)} · {bytes(c.file.bytes)} · {number(c.num_timesteps,0)}단계 / {number(c.updates,0)} 업데이트</p><Status tone={c.compatible?'good':'warn'}>{c.compatible?'현재 설정 식별정보와 호환':'이전 환경 / 정보 부족'}</Status></div><div className="flex gap-3"><a className="text-xs font-semibold text-blue-600" href={'/api/checkpoint?path='+encodeURIComponent(c.path)} download>정책 다운로드</a><Button disabled={!c.compatible||s.job.running} busy={pending.has('checkpoints/restore')} onClick={async()=>{setError('');try{const r=await execute<{message:string}>('checkpoints/restore',{path:c.path});setMessage(r.message)}catch(e){setError(e instanceof Error?e.message:'복원 실패')}}}>버전 복원·선택</Button></div></div>):<Empty title="저장된 정책 파일이 없습니다."/>}
 <ErrorMessage message={error}/>{message&&<p className="mt-3 text-xs text-emerald-700">{message}</p>}
 <div className="mt-4"><Capability name="checkpoint_restore" label="과거 정책 버전 복원"/></div>
 </Panel>;
}
