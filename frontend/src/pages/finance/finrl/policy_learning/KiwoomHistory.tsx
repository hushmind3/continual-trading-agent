import {useEffect,useRef,useState} from 'react';
import {request} from '../../../../data/api';
import {useOperations} from '../../../../data/Operations';
import {Panel} from '../../../../ui/Panel';
import {Button,ErrorMessage} from '../../../../ui/Primitives';
import {number} from '../../../../ui/format';

type History={status:string;rows:number;symbols:{symbol:string;rows:number;start:string;end:string}[];errors:{symbol:string;error:string}[];error?:string};
export function KiwoomHistory(){
 const {refresh}=useOperations(),[result,setResult]=useState<History|null>(null),[error,setError]=useState(''),[pending,setPending]=useState(false);
 const refreshRef=useRef(refresh);refreshRef.current=refresh;
 useEffect(()=>{let alive=true,timer:ReturnType<typeof setTimeout>|undefined;
  async function poll(){try{const next=await request<History>('price/history',{},'GET');if(!alive)return;setResult(next);if(next.status==='running')timer=setTimeout(poll,2000);else if(next.status==='completed'||next.status==='partial')void refreshRef.current();}catch(e){if(alive)setError(e instanceof Error?e.message:String(e));}}
  void poll();return()=>{alive=false;if(timer)clearTimeout(timer)};
 },[pending]);
 async function collect(){setError('');setPending(true);try{setResult(await request<History>('price/history',{}));}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setPending(false)}}
 const busy=pending||result?.status==='running';
 return <Panel title="키움 학습 데이터" description="등록된 국내 주식·ETF의 완료된 수정 일봉을 키움에서 받아 기존 가격 저장소에 반영합니다. 오늘 진행 중인 봉은 제외합니다.">
  <Button tone="primary" busy={busy} onClick={()=>void collect()}>키움 가격 수집</Button>
  {result&&<p className="mt-3 text-sm">{({running:'수집 중',completed:'수집 완료',partial:'일부 수집 실패',failed:'수집 실패',interrupted:'완료 미확인',idle:'수집 기록 없음'} as Record<string,string>)[result.status]??result.status} · {number(result.rows,0)}행 · {number(result.symbols.length,0)}종목</p>}
  <ErrorMessage message={error||result?.error||''}/>
  {!!result?.errors.length&&<ul className="mt-3 text-xs text-red-600">{result.errors.map(item=><li key={item.symbol}>{item.symbol}: {item.error}</li>)}</ul>}
  {!!result?.symbols.length&&<details className="mt-3 text-xs text-slate-500"><summary>실제 저장 범위</summary>{result.symbols.map(item=><p key={item.symbol}>{item.symbol} · {item.start} ~ {item.end} · {number(item.rows,0)}행</p>)}</details>}
 </Panel>;
}
