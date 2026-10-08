import {useState} from "react";
import {ArrowDownLeft,ArrowUpRight,Wallet} from "lucide-react";
import {useOperations} from "../data/Operations";
import type {Currency} from "../data/types";
import {ControlButton} from "../ui/ControlButton";
import {Empty,Meter,Skeleton,Sparkline,Tabs} from "../ui/Primitives";
import {accountNames,date,money,number,percent} from "../ui/format";
import {Fills} from "./portfolio/Fills";
import {Positions} from "./portfolio/Positions";

export function PortfolioWorkspace(){
 const {state}=useOperations();
 const [currency,setCurrency]=useState<Currency>(()=>sessionStorage.getItem('portfolio_currency')==='KRW'?'KRW':'USD'),[tab,setTab]=useState("positions");
 if(!state)return <Skeleton/>;
 const book=state.account?.books[currency],history=state.equity_history[currency]??[];
 return <div className="space-y-5">
  <div className="flex flex-wrap items-center justify-between gap-3">
   <Tabs items={[{id:"KRW",label:"국내주식 · KRW"},{id:"USD",label:"미국주식 · USD"}]} value={currency} onChange={value=>{sessionStorage.setItem('portfolio_currency',value);setCurrency(value as Currency)}}/>
   <ControlButton name="paper" label="두 계좌 가상체결"/>
  </div>
  <p className="text-xs text-slate-500">원화와 달러는 잔고·손익·주문·체결을 각각 계산하는 독립 가상계좌입니다. 환전하거나 두 금액을 합산하지 않습니다.</p>
  {!book?<Empty title="이 가상계좌의 상태가 아직 없습니다."/>:<>
   <section className="grid gap-6 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200/50 lg:grid-cols-[1fr_1.15fr]">
    <div>
     <h2 className="flex items-center gap-2 text-sm font-bold text-slate-700"><Wallet size={17}/>{accountNames[currency]}</h2>
     <p className="mt-4 text-xs text-slate-400">이 계좌의 총 평가금액</p><p className="mt-2 text-4xl font-bold tabular-nums">{money(book.equity,currency)}</p>
     <p className={`mt-3 flex items-center gap-1 text-sm font-semibold ${book.pnl>=0?'text-rose-500':'text-blue-500'}`}>{book.pnl>=0?<ArrowUpRight size={16}/>:<ArrowDownLeft size={16}/>} {money(book.pnl,currency)} ({percent(book.return_rate)})</p>
     <dl className="mt-5 grid grid-cols-3 gap-3 text-xs"><div><dt className="text-slate-400">초기 자금</dt><dd className="mt-1 font-semibold">{money(book.initial_cash,currency)}</dd></div><div><dt className="text-slate-400">누적 체결</dt><dd className="mt-1 font-semibold">{number(book.trade_count,0)}회</dd></div><div><dt className="text-slate-400">보유 종목</dt><dd className="mt-1 font-semibold">{book.positions.length}개</dd></div></dl>
    </div>
    <div><div className="mb-3 flex items-center justify-between text-xs text-slate-400"><span>{currency} 가상계좌 평가 기록</span><span>{date(history.at(-1)?.as_of)}</span></div>
     <Sparkline values={history.map(point=>point.equity)} up={book.pnl>=0} height={100}/>
     <div className="mt-4 flex justify-between text-xs text-slate-500"><span>현금 {money(book.cash,currency)}</span><span>보유 평가액 {money(book.equity-book.cash,currency)}</span></div>
     <div className="mt-2"><Meter value={book.equity>0?(book.equity-book.cash)/book.equity*100:0}/></div>
    </div>
   </section>
   <div className="flex flex-wrap items-center justify-between gap-3">
    <Tabs items={[{id:"positions",label:`보유 종목 ${book.positions.length}`},{id:"fills",label:"체결 원장"}]} value={tab} onChange={setTab}/>
    <span className="text-xs text-slate-500">이 계좌의 누적 비용 {money(book.fees+book.slippage+book.spread+book.sell_tax,currency)}</span>
   </div>
   {tab==='positions'?<Positions key={currency} book={book} currency={currency}/>:<Fills key={currency} currency={currency}/>}
   <p className="text-xs text-slate-400">가상체결 · 다음 완료 시세 · 수수료 {percent(state.settings.risk.fee)} · 가격 미끄러짐 {percent(state.settings.risk.slippage)}</p>
  </>}
 </div>;
}
