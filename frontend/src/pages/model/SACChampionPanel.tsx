import {useMemo,useState} from 'react';
import {WandSparkles,X} from 'lucide-react';
import {request} from '../../data/api';
import type {Currency,Instrument} from '../../data/types';
import {Button,ErrorMessage,inputClass} from '../../ui/Primitives';
import {Panel} from '../../ui/Panel';
import {DataTable,type Column} from '../../ui/DataTable';
import {bytes,number} from '../../ui/format';

interface Result {name:string;path:string;checkpoint:string;file_bytes:number;trained:boolean;parameters:Record<string,number>}
export function SACChampionPanel({items,initialExpertIds,onClose}:{items:Instrument[];initialExpertIds:string[];onClose:()=>void}){
 const [currency,setCurrency]=useState<Currency>('USD'),[symbols,setSymbols]=useState<string[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false),[result,setResult]=useState<Result|null>(null);
 const markets=useMemo(()=>items.filter(i=>i.currency===currency&&i.eligible&&i.stored),[items,currency]);
 const columns=useMemo<Column<Instrument>[]>(()=>[{key:'symbol',label:'종목',render:r=>r.symbol,sort:r=>r.symbol},{key:'name',label:'이름',render:r=>r.name},{key:'observations',label:'관측',render:r=>number(r.observations,0),sort:r=>r.observations}],[]);
 const create=async()=>{setError('');setResult(null);setBusy(true);try{const value=await request<Result>('champions/create',{currency,symbols:[...symbols].sort(),experts:[...initialExpertIds].sort()});setResult(value)}catch(e){setError(e instanceof Error?e.message:'SAC Champion 생성 실패')}finally{setBusy(false)}};
 return <Panel title="SAC Champion 생성" description={`선택한 Expert ${initialExpertIds.length}개로 생성합니다.`} actions={<Button disabled={busy} onClick={onClose}><X size={15}/>닫기</Button>}>
  <label className="mb-4 block max-w-xs text-xs text-slate-500">시장<select className={inputClass+' mt-2'} value={currency} disabled={busy} onChange={e=>{setCurrency(e.target.value as Currency);setSymbols([])}}><option value="USD">USD · 미국</option><option value="KRW">KRW · 한국</option></select></label>
  <h3 className="mb-2 text-sm font-semibold">종목 선택</h3><DataTable items={markets} columns={columns} label="Champion 시장 종목" keyFor={r=>r.symbol} searchText={r=>r.symbol+' '+r.name} select={{checked:r=>symbols.includes(r.symbol),disabled:r=>busy||r.observations<=252,toggle:r=>setSymbols(old=>old.includes(r.symbol)?old.filter(s=>s!==r.symbol):[...old,r.symbol])}}/>
  <div className="mt-4 flex flex-wrap items-center gap-3"><Button tone="primary" busy={busy} disabled={busy||!symbols.length} onClick={()=>void create()}><WandSparkles size={15}/>SAC Champion 생성</Button><span className="text-xs text-slate-500">종목 {symbols.length}개 · 선택 Expert {initialExpertIds.length}개</span></div>
  <ErrorMessage message={error}/>
  {result&&<div role="status" className="mt-4 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-900"><b>{result.name} 생성 완료</b><p className="mt-1 text-xs">PT: {result.path} · {bytes(result.file_bytes)}</p><p className="text-xs">SB3 체크포인트: {result.checkpoint} · {number(result.parameters?.total_logical_parameters,0)} parameters</p></div>}
 </Panel>;
}
