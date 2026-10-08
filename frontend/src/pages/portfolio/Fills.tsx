import {useEffect,useState} from 'react';
import type {Currency,Fill} from '../../data/types';
import {request} from '../../data/api';
import {Button,Empty,ErrorMessage,Skeleton} from '../../ui/Primitives';
import {accountNames,date,money,number} from '../../ui/format';

interface Page {fills:Fill[];recorded:number;cumulative:number;missing:number}
export function Fills({currency}:{currency:Currency}){
 const [page,setPage]=useState<Page|null>(null),[items,setItems]=useState<Fill[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{
  let active=true;setPage(null);setItems([]);setError('');
  const refresh=async()=>{
   try{const next=await request<Page>(`fills?currency=${currency}&limit=50`);
    if(active){setPage(next);setItems(old=>[...new Map([...old,...next.fills].map(f=>[f.sequence,f])).values()].sort((a,b)=>b.sequence-a.sequence));setError('')}
   }catch(e){if(active)setError(e instanceof Error?e.message:'체결 조회 실패')}
  };
  void refresh();const timer=setInterval(()=>void refresh(),5000);return()=>{active=false;clearInterval(timer)};
 },[currency]);
 const more=async()=>{
  setBusy(true);try{const next=await request<Page>(`fills?currency=${currency}&limit=50&before=${items.at(-1)?.sequence}`);
   setItems(old=>[...old,...next.fills]);setPage(next);setError('');
  }catch(e){setError(e instanceof Error?e.message:'체결 조회 실패')}finally{setBusy(false)}
 };
 if(!page)return error?<ErrorMessage message={error}/>:<Skeleton/>;
 return <section className="space-y-4">
  <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
   <strong className="text-slate-700">{accountNames[currency]} 체결 원장</strong>
   <span>누적 {number(page.cumulative,0)}회 · 저장된 기록 {number(page.recorded,0)}건</span>
  </div>
  {page.missing>0&&<p className="rounded-xl bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-800">이전 체결 {number(page.missing,0)}건은 기존 공용 기록이 삭제되어 원장에 없습니다. 새 체결은 통화별로 계속 저장하며, 없는 과거 기록을 생성하지 않습니다.</p>}
  {error&&<ErrorMessage message={error}/>}
  {items.length?<div className="overflow-x-auto rounded-2xl bg-white">
   <table className="w-full text-left text-sm"><thead className="border-b border-slate-100 text-xs text-slate-400"><tr>
    {['번호','체결 시각','종목','매수 · 매도','수량','체결가','수수료'].map(label=><th key={label} className="whitespace-nowrap px-4 py-3 font-medium">{label}</th>)}
   </tr></thead><tbody>{items.map(fill=><tr key={fill.sequence} className="border-b border-slate-50 last:border-0">
    <td className="px-4 py-3 text-xs text-slate-400">{number(fill.sequence,0)}</td>
    <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-400"><time title={fill.date}>{date(fill.date)}</time></td>
    <td className="px-4 py-3 font-semibold">{fill.symbol}</td><td className={`px-4 py-3 ${fill.action==='BUY'?'text-rose-500':'text-blue-500'}`}>{fill.action==='BUY'?'매수':'매도'}</td>
    <td className="px-4 py-3 tabular-nums">{number(fill.quantity,4)}주</td><td className="px-4 py-3 tabular-nums">{money(fill.price,currency)}</td><td className="px-4 py-3 text-slate-400">{money(fill.fee??0,currency)}</td>
   </tr>)}</tbody></table>
  </div>:<Empty title={page.cumulative?'현재 보관된 체결 기록이 없습니다.':'이 계좌의 체결이 아직 없습니다.'}/>}
  {items.length<page.recorded&&<Button busy={busy} onClick={()=>void more()}>이전 체결 더 보기</Button>}
 </section>;
}
