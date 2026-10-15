import {useMemo,useState} from 'react';
import {AccountEquityHistory} from './AccountEquityHistory';
import {Wallet,ArrowUpRight,ArrowDownRight} from 'lucide-react';
import type {Currency} from '../../../../data/types';
import {useOperations} from '../../../../data/Operations';
import {Panel} from '../../../../ui/Panel';
import {Button,Empty,ErrorMessage,Skeleton,Tabs,inputClass} from '../../../../ui/Primitives';
import {DataTable,type Column} from '../../../../ui/DataTable';
import {money,number,date} from '../../../../ui/format';
export function PaperAccounts({currency}:{currency:Currency}) {
 const {state:s,execute,pending}=useOperations();const [symbol,setSymbol]=useState(''),[quantity,setQuantity]=useState(1),[tab,setTab]=useState('positions'),[error,setError]=useState(''),[message,setMessage]=useState('');
 const fills=s?.operations?.account.fills.filter(f=>f.currency===currency)||[];
 const names=useMemo(()=>new Map(s?.data.instruments.map(item=>[item.symbol,item.name])??[]),[s?.data.instruments]);
 const amount=(value:unknown)=>typeof value==='number'&&Number.isFinite(value)?money(value,currency):'미수신';
 const fillColumns=useMemo<Column<Record<string,unknown>>[]>(()=>[
  {key:'symbol',label:'종목',render:r=>{const code=String(r.symbol??'');const name=names.get(code);return <div className="account-instrument"><b>{name||code||'미기록'}</b>{name&&name!==code&&<span>{code}</span>}</div>}},
  {key:'action',label:'구분',render:r=><span className={r.action==='BUY'?'account-buy-label':r.action==='SELL'?'account-sell-label':''}>{r.action==='BUY'?'매수':r.action==='SELL'?'매도':String(r.action??'미기록')}</span>},
  {key:'quantity',label:'수량',render:r=>number(typeof r.quantity==='number'?r.quantity:undefined,0),sort:r=>typeof r.quantity==='number'?r.quantity:0},
  {key:'price',label:'체결가',render:r=>amount(r.price)},
  {key:'timestamp',label:'체결 시각',render:r=>date(typeof r.timestamp==='string'||typeof r.timestamp==='number'?r.timestamp:undefined),sort:r=>String(r.timestamp??'')},
  {key:'fee',label:'수수료',render:r=>amount(r.fee)},
  {key:'realized_pnl',label:'실현 손익',render:r=>amount(r.realized_pnl)}],[currency,names]);
 if(!s?.operations)return <Skeleton/>;const book=s.operations.account.books[currency];
 if(!book)return <Empty title="계좌 상태를 확인할 수 없습니다." detail="운영 화면에서 계좌 상태를 확인하세요."/>;
 const rows=Object.entries(book.positions).map(([code,p])=>({symbol:code,name:names.get(code)??code,...p,mark:book.marks[code]}));
 const order=async(action:'BUY'|'SELL')=>{setError('');setMessage('');try{const r=await execute<{price_source:string}>('orders',{symbol,currency,action,quantity});setMessage('체결 기록 저장 · '+(r.price_source==='live'?'수신 시세':'실제 저장 가격')+' 기준')}catch(e){setError(e instanceof Error?e.message:'주문 실패')}};
 const totalReturn=Number.isFinite(book.initial_cash)&&book.initial_cash>0&&Number.isFinite(book.net_pnl)?book.net_pnl/book.initial_cash*100:null;
 const pnlClass=book.net_pnl>0?'account-pnl-positive':book.net_pnl<0?'account-pnl-negative':'';
 return <div className="account-detail-layout"><Panel title={currency==='KRW'?'원화 가상계좌':'달러 가상계좌'} description="가상매매 원장입니다. 증권사에 실제 주문을 전송하지 않습니다." className="account-overview" collapsible={false}>
 <div className="account-balance"><div><span className="account-balance-eyebrow">{currency==='KRW'?'KRW ACCOUNT':'USD ACCOUNT'}</span><p>총 평가자산</p><strong>{amount(book.equity)}</strong></div><span className="account-wallet"><Wallet size={24}/></span></div>
 <div className="account-metrics"><div><p>현금 잔고</p><strong>{amount(book.cash)}</strong></div><div><p>보유 평가</p><strong>{amount(book.holdings_value)}</strong></div><div><p>총 손익</p><strong className={pnlClass}>{amount(book.net_pnl)}</strong></div></div>
 <div className="account-summary-footer"><span>초기자금 대비 <strong>{totalReturn==null?'미측정':(totalReturn>0?'+':'')+number(totalReturn,2)+'%'}</strong></span><span>실현 손익 <strong>{amount(book.realized_pnl)}</strong></span><span>누적 체결 <strong>{number(book.trade_count,0)}건</strong></span></div>
 </Panel>
 <AccountEquityHistory history={book.equity_history} currency={currency}/>
 <Panel title="보유와 체결" className="account-records" collapsible={false}><Tabs value={tab} onChange={setTab} items={[{id:'positions',label:'보유 종목 '+rows.length},{id:'fills',label:'체결 내역 '+fills.length}]}/>
 <div className="mt-5">{tab==='positions'?rows.length?<DataTable label="가상계좌 보유" items={rows} keyFor={r=>r.symbol} searchText={r=>r.symbol+' '+r.name} columns={[{key:'symbol',label:'종목',render:r=><div className="account-instrument"><b>{r.name}</b>{r.name!==r.symbol&&<span>{r.symbol}</span>}</div>,sort:r=>r.symbol},{key:'qty',label:'보유 수량',render:r=>number(r.quantity,0),sort:r=>r.quantity},{key:'avg',label:'평균 단가',render:r=>amount(r.average_cost)},{key:'mark',label:'평가 가격',render:r=>r.mark==null?'시세 대기':amount(r.mark)},{key:'pnl',label:'평가 손익',render:r=>r.mark==null?'시세 대기':<span className={(r.mark-r.average_cost)>0?'account-pnl-positive':(r.mark-r.average_cost)<0?'account-pnl-negative':''}>{amount((r.mark-r.average_cost)*r.quantity)}</span>}]}/>:<Empty title="보유 종목이 없습니다."/>:fills.length?<DataTable label="가상 체결" items={fills} keyFor={r=>String(r.sequence??r.id??fills.indexOf(r))} searchText={r=>[r.symbol,names.get(String(r.symbol??'')),r.action==='BUY'?'매수':r.action==='SELL'?'매도':r.action,r.timestamp].join(' ')} columns={fillColumns}/>:<Empty title="아직 가상체결 기록이 없습니다."/>}</div>
 </Panel>
 <details className="workspace-disclosure account-manual-order"><summary>수동 가상 주문</summary><div className="account-order-form"><label>종목<select aria-label="가상 주문 종목" className={inputClass} value={symbol} onChange={e=>setSymbol(e.target.value)}><option value="">종목 선택</option>{s.data.instruments.filter(i=>i.eligible&&i.currency===currency).map(i=><option key={i.symbol} value={i.symbol}>{i.name} · {i.symbol}</option>)}</select></label><label>수량<input aria-label="가상 주문 수량" type="number" min={1} step={1} className={inputClass} value={quantity} onChange={e=>setQuantity(Number(e.target.value))}/></label><Button tone="primary" disabled={!symbol||!Number.isInteger(quantity)||quantity<1} busy={pending.has('orders')} onClick={()=>void order('BUY')}><ArrowUpRight size={15}/>가상 매수</Button><Button tone="danger" disabled={!symbol||!Number.isInteger(quantity)||quantity<1} busy={pending.has('orders')} onClick={()=>void order('SELL')}><ArrowDownRight size={15}/>가상 매도</Button></div>
 {(!Number.isInteger(quantity)||quantity<1)&&<p role="alert" className="mb-3 text-xs text-rose-700">수량은 1 이상의 정수로 입력하세요.</p>}<ErrorMessage message={error}/>{message&&<p className="mt-3 text-xs text-emerald-700">{message}</p>}
 </details></div>;
}
