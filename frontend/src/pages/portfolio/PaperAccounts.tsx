import {useMemo,useState} from 'react';
import type {Currency} from '../../data/types';
import {useOperations} from '../../data/Operations';
import {Panel,KeyValues} from '../../ui/Panel';
import {Button,ErrorMessage,Tabs,inputClass} from '../../ui/Primitives';
import {DataTable,type Column} from '../../ui/DataTable';
import {OperationsControls} from '../../ui/OperationsControls';
import {money,number} from '../../ui/format';
export function PaperAccounts({currency}:{currency:Currency}) {
 const {state:s,execute,pending}=useOperations();const [symbol,setSymbol]=useState(''),[quantity,setQuantity]=useState(1),[tab,setTab]=useState('positions'),[error,setError]=useState(''),[message,setMessage]=useState('');
 const fills=s?.operations?.account.fills.filter(f=>f.currency===currency)||[];
 const fillColumns=useMemo<Column<Record<string,unknown>>[]>(()=>['symbol','action','quantity','price','timestamp','fee','realized_pnl'].map(key=>({key,label:key,render:r=>String(r[key]??'미기록')})),[]);
 if(!s?.operations)return null;const book=s.operations.account.books[currency];
 const rows=Object.entries(book.positions).map(([code,p])=>({symbol:code,...p,mark:book.marks[code]??p.average_cost}));
 const order=async(action:'BUY'|'SELL')=>{setError('');setMessage('');try{const r=await execute<{price_source:string}>('orders',{symbol,currency,action,quantity});setMessage('체결 기록 저장 · '+(r.price_source==='live'?'수신 시세':'실제 저장 가격')+' 기준')}catch(e){setError(e instanceof Error?e.message:'주문 실패')}};
 return <Panel title={currency+' 가상매매 계좌'} description="복구한 PaperAccount · 실제 주문을 증권사에 전송하지 않습니다." actions={<OperationsControls/>}>
 <KeyValues items={[['잔고',money(book.cash,currency)],['총 평가',money(book.equity,currency)],['보유 평가',money(book.holdings_value,currency)],['총 손익',money(book.net_pnl,currency)],['실현 손익',money(book.realized_pnl,currency)],['누적 체결',number(book.trade_count,0)]]}/>
 <div className="my-5 flex flex-wrap items-end gap-3"><label className="text-xs text-slate-500">종목<select className={inputClass+' mt-2'} value={symbol} onChange={e=>setSymbol(e.target.value)}><option value="">선택</option>{s.data.instruments.filter(i=>i.eligible&&i.currency===currency).map(i=><option key={i.symbol} value={i.symbol}>{i.name} · {i.symbol}</option>)}</select></label><label className="text-xs text-slate-500">수량<input type="number" min={1} className={inputClass+' mt-2 !w-28'} value={quantity} onChange={e=>setQuantity(Number(e.target.value))}/></label><Button tone="primary" disabled={!symbol||quantity<1} busy={pending.has('orders')} onClick={()=>void order('BUY')}>가상 매수</Button><Button tone="danger" disabled={!symbol||quantity<1} busy={pending.has('orders')} onClick={()=>void order('SELL')}>가상 매도</Button></div>
 <ErrorMessage message={error}/>{message&&<p className="mb-4 text-xs text-emerald-700">{message}</p>}
 <Tabs value={tab} onChange={setTab} items={[{id:'positions',label:'보유 종목'},{id:'fills',label:'가상체결 원장'}]}/>
 <div className="mt-4">{tab==='positions'?<DataTable label="가상계좌 보유" items={rows} keyFor={r=>r.symbol} columns={[{key:'symbol',label:'종목',render:r=>r.symbol},{key:'qty',label:'보유 수량',render:r=>number(r.quantity,0)},{key:'avg',label:'평균 단가',render:r=>money(r.average_cost,currency)},{key:'mark',label:'평가 가격',render:r=>money(r.mark,currency)},{key:'pnl',label:'평가 손익',render:r=>money((r.mark-r.average_cost)*r.quantity,currency)}]}/>:<DataTable label="가상 체결" items={fills} keyFor={r=>String(r.sequence??r.id??fills.indexOf(r))} columns={fillColumns}/>}</div>
 </Panel>;
}
