import type {Book,Currency,Position} from './api/types';
export function numeric(value:unknown):number|undefined {if(value===null||value===undefined||value==='')return undefined;const n=Number(value);return Number.isFinite(n)?n:undefined;}
export const number=(v:unknown,digits=0)=>numeric(v)===undefined?'미수신':new Intl.NumberFormat('ko-KR',{maximumFractionDigits:digits}).format(Number(v));
export const money=(v:unknown,currency:Currency)=>numeric(v)===undefined?'미수신':new Intl.NumberFormat('ko-KR',{style:'currency',currency,maximumFractionDigits:currency==='KRW'?0:2}).format(Number(v));
export const percent=(v:unknown)=>numeric(v)===undefined?'미수신':`${number(Number(v)*100,2)}%`;
export const seconds=(v:unknown)=>numeric(v)===undefined?'기록 없음':`${number(v,3)}초`;
export function bytes(v:unknown){const n=numeric(v);if(n===undefined)return '측정 없음';if(n===0)return '0 B';const i=Math.min(3,Math.floor(Math.log(n)/Math.log(1024)));return `${number(n/1024**i,2)} ${['B','KB','MB','GB'][i]}`;}
export function date(value?:string){if(!value)return '기록 없음';const d=new Date(value);return Number.isNaN(d.getTime())?value:new Intl.DateTimeFormat('ko-KR',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Seoul'}).format(d).replace('. ','/').replace('.','');}
export const pnlColor=(v:unknown)=>Number(v)>0?'text-rose-400':Number(v)<0?'text-sky-400':'text-slate-400';
export const stateLabel=(s?:string)=>({stopped:'정지',running:'실행 중',loading:'모델 적재 중',starting:'시작 중',saving:'저장 중',stopping:'정지 처리 중',paused:'일시 정지',replay:'과거 데이터 평가',paper:'가상매매 평가',promoted:'승격',rejected:'탈락',queued:'대기',complete:'완료',installed:'장착',created:'생성',error:'오류'}[s??'']??s??'상태 미수신');
export const actionLabel=(s?:string)=>({BUY:'매수',HOLD:'유지',SELL:'매도'}[s??'']??'판단 대기');
const names:Record<string,string>={'^DJI':'다우존스','^IXIC':'나스닥','^GSPC':'S&P 500','^FTSE':'FTSE 100','^N225':'닛케이','^HSI':'항셍','^VIX':'변동성 지수','^KS11':'코스피','^KQ11':'코스닥','^TNX':'미국 10년 국채','^FVX':'미국 5년 국채','^TYX':'미국 30년 국채','US_Treasury':'미국 국채','HongKong':'홍콩',AAPL:'애플',MSFT:'마이크로소프트',NVDA:'엔비디아',AMZN:'아마존',GOOGL:'알파벳',TSLA:'테슬라',AVGO:'브로드컴',LRCX:'램리서치',ETHUSDT:'ETH / USDT','BTC-USD':'비트코인','ETH-USD':'이더리움'};
export function symbolName(s:string,name?:string){const key=s.replace(/_+$/,'');return names[key]??(name&&name!==s?names[name]??name:key);}
export function positions(book:Book):Position[]{if(Array.isArray(book.positions))return book.positions;return Object.entries(book.positions??{}).map(([symbol,p])=>{const mark=book.marks?.[symbol]??p.mark;return {...p,symbol,mark,...(mark===undefined?{}:{value:mark*Number(p.quantity),unrealized_pnl:(mark-Number(p.average_cost))*Number(p.quantity)})};});}
export function netPnl(book:Book){return book.net_pnl??(book.equity===undefined||book.initial_cash===undefined?undefined:book.equity-book.initial_cash);}
