import {useCallback,useState} from 'react';
import type {Book,Currency} from '../../data/types';
import {Drawer,Empty} from '../../ui/Primitives';
import {accountNames,money,number,percent} from '../../ui/format';
import {useOperations} from '../../data/Operations';

export function Positions({book,currency}:{book:Book;currency:Currency}){
 const {state}=useOperations();const [selected,setSelected]=useState<string|null>(null);
 const close=useCallback(()=>setSelected(null),[]);
 const list=[...book.positions].sort((a,b)=>b.value-a.value),item=list.find(p=>p.symbol===selected);
 const decision=state?.decisions.find(d=>d.symbol===selected&&d.currency===currency);
 if(!list.length)return <Empty title="이 계좌의 보유 종목이 없습니다."/>;
 return <section className="space-y-4">
  <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
   <strong>{accountNames[currency]} · {list.length}종목</strong><span>1주 보유 {list.filter(p=>p.quantity===1).length}종목 · 평가금액 순</span>
  </div>
  <div className="max-h-[60dvh] overflow-auto rounded-2xl bg-white"><table className="w-full text-left text-sm">
   <thead className="sticky top-0 bg-white border-b border-slate-100 text-xs text-slate-400"><tr>{['종목','보유 수량','평가금액','현재 비중','미실현 손익'].map(label=><th key={label} className="whitespace-nowrap px-4 py-3 font-medium">{label}</th>)}</tr></thead>
   <tbody>{list.map(p=><tr key={p.symbol} tabIndex={0} aria-selected={selected===p.symbol} onClick={()=>setSelected(p.symbol)}
    onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setSelected(p.symbol)}}}
    className="cursor-pointer border-b border-slate-50 outline-none transition hover:bg-blue-50/50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-400">
    <td className="px-4 py-3"><b>{p.name??p.symbol}</b>{p.name!==p.symbol&&<div className="mt-1 text-xs text-slate-400">{p.symbol}</div>}</td>
    <td className="px-4 py-3 tabular-nums">{number(p.quantity,0)}주</td><td className="px-4 py-3 tabular-nums">{money(p.value,currency)}</td>
    <td className="px-4 py-3 tabular-nums">{percent(p.value/book.equity)}</td><td className={`px-4 py-3 tabular-nums ${p.pnl>=0?'text-rose-500':'text-blue-500'}`}>{money(p.pnl,currency)}</td>
   </tr>)}</tbody></table></div>
  <Drawer title={item?.name??item?.symbol??'보유 종목'} open={Boolean(item)} onClose={close}>{item&&<div className="space-y-5">
   <p className="text-xs text-slate-400">{accountNames[currency]} · {item.symbol}</p><p className="text-3xl font-bold">{money(item.value,currency)}</p>
   <dl className="grid grid-cols-2 gap-4 text-sm">{[['보유 수량',`${item.quantity}주`],['평균 매입가',money(item.average_cost,currency)],['평가에 사용한 가격',money(item.mark,currency)],['현재 비중',percent(item.value/book.equity)],['미실현 손익',money(item.pnl,currency)],...(decision?[['최근 목표 비중',percent(decision.target_weight)]]:[])].map(([label,value])=><div key={label}><dt className="text-xs text-slate-400">{label}</dt><dd className="mt-1 font-semibold">{value}</dd></div>)}</dl>
  </div>}</Drawer>
 </section>;
}
