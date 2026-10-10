import {useCallback,useMemo,useState} from 'react';
import {Search} from 'lucide-react';
import {useOperations} from '../data/Operations';
import {useEndpoint} from '../data/useEndpoint';
import type {Instrument,Bar} from '../data/types';
import {Button,Drawer,ErrorMessage,Skeleton,Sparkline,inputClass} from '../ui/Primitives';
import {Panel,KeyValues} from '../ui/Panel';
import {DataTable,type Column} from '../ui/DataTable';
import {number,money,marketName} from '../ui/format';
import {CollectionPanel} from './markets/CollectionPanel';
export function MarketScanner(){const {state:s}=useOperations();
 const [market,setMarket]=useState('all'),[selected,setSelected]=useState<string|null>(null),[limit,setLimit]=useState(300);
 const close=useCallback(()=>setSelected(null),[]);
 const history=useEndpoint<{symbol:string;rows:Bar[]}>(selected?'prices?symbol='+encodeURIComponent(selected)+'&limit='+limit:null);
 const columns=useMemo<Column<Instrument>[]>(()=>[
 {key:'name',label:'종목',render:r=><Button className="!bg-transparent !p-0 !text-left" onClick={()=>setSelected(r.symbol)}><span>{r.name}<small className="mt-1 block text-left font-normal text-slate-400">{r.symbol}</small></span></Button>,sort:r=>r.name},
 {key:'market',label:'시장',render:r=>marketName(r.market)},{key:'price',label:'마지막 저장 가격',render:r=>r.last_close!=null?money(r.last_close,r.currency):'가격 없음',sort:r=>r.last_close??-1},
 {key:'days',label:'거래 날짜 수',render:r=>number(r.trading_days,0),sort:r=>r.trading_days},{key:'rows',label:'가격 행',render:r=>number(r.rows,0)},
 {key:'date',label:'최근 저장 시점',render:r=>r.end||'없음',sort:r=>r.end||''},
 {key:'eligible',label:'학습 대상',render:r=>r.eligible?'등록 주식·ETF':'조회 전용'},
 ],[]);
 const barColumns=useMemo<Column<Bar>[]>(()=>[
 {key:'date',label:'시각',render:r=>r.date},...(['open','high','low','close','volume'] as const).map(key=>({key,label:({open:'시가',high:'고가',low:'저가',close:'종가',volume:'거래량'})[key],render:(r:Bar)=>number(r[key],key==='volume'?0:3)}))
 ],[]);
 if(!s)return <Skeleton/>;const item=s.data.instruments.find(r=>r.symbol===selected);
 return <div className="space-y-5"><div className="flex flex-wrap items-center justify-between gap-4"><div className="flex items-center gap-3"><Search size={17} className="text-blue-500"/><select aria-label="시장 필터" className={inputClass+' !w-auto'} value={market} onChange={e=>setMarket(e.target.value)}><option value="all">모든 시장</option>{[...new Set(s.data.instruments.map(r=>r.market))].sort().map(m=><option key={m} value={m}>{marketName(m)}</option>)}</select></div><p className="text-xs text-slate-500">저장 가격 조회 · 실시간 공급원과 구분</p></div>
 <Panel title="시장 · 실제 가격 저장소" description="공식 DataStore에 저장된 가격과 등록 종목을 조회합니다."><KeyValues items={[['종목 수',number(s.data.tickers,0)],['가격 행',number(s.data.rows,0)],['시작',s.data.start],['종료',s.data.end]]}/>{s.data.error&&<ErrorMessage message={s.data.error}/>}<DataTable label="시장 종목" items={s.data.instruments.filter(r=>market==='all'||r.market===market)} columns={columns} keyFor={r=>r.symbol} searchText={r=>r.name+' '+r.symbol}/></Panel>
 <CollectionPanel/>
 <Drawer title={item?.name||'종목 상세'} open={!!selected} onClose={close}>{item&&<div className="space-y-5"><KeyValues items={[['코드',item.symbol],['통화',item.currency],['기간',item.start?.slice(0,10)+' ~ '+item.end?.slice(0,10)],['가격 관측',number(item.observations,0)]]}/><Button tone="primary" disabled={!item.eligible||!item.stored} onClick={()=>{sessionStorage.setItem('training_symbols',JSON.stringify([item.symbol]));sessionStorage.setItem('training_currency',item.currency);close();location.hash='learning'}}>이 종목으로 학습 선택</Button><label className="block text-xs text-slate-500">가격 조회 개수<select aria-label="가격 조회 개수" value={limit} className={inputClass+' mt-2'} onChange={e=>setLimit(Number(e.target.value))}><option value={100}>100개</option><option value={300}>300개</option><option value={1000}>1,000개</option><option value={2000}>2,000개</option></select></label>{history.error&&<ErrorMessage message={history.error}/>}<Sparkline values={history.data?.rows.map(r=>r.close).filter((v):v is number=>v!=null)||[]} height={110}/>{history.data&&<DataTable label="OHLCV" items={history.data.rows} columns={barColumns} keyFor={r=>r.date}/>}</div>}</Drawer>
 </div>;
}
