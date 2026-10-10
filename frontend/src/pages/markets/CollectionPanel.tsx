import {useState} from 'react';
import {Download} from 'lucide-react';
import {useOperations} from '../../data/Operations';
import {useEndpoint} from '../../data/useEndpoint';
import type {Connections} from '../../data/types';
import {Panel} from '../../ui/Panel';
import {Button,ErrorMessage,Status,inputClass} from '../../ui/Primitives';
export function CollectionPanel(){const {state:s,execute,pending}=useOperations();const connection=useEndpoint<Connections>('connections');const [symbols,setSymbols]=useState(''),[start,setStart]=useState(''),[end,setEnd]=useState(''),[error,setError]=useState(''),[message,setMessage]=useState('');
 const configured=connection.data?.data.status==='configured';
 return <Panel title="공식 데이터 수집" description="FinRL-X fetch_price_data · FMP 공급원 · 원본 모듈이 DB 저장" actions={<Status tone={configured?'good':'warn'}>{configured?'인증 설정 있음 · 원격 검증 전':'인증 / 모듈 상태 확인 필요'}</Status>}>
 {connection.error&&<ErrorMessage message={connection.error}/>}<p className="mb-4 text-xs leading-6 text-slate-500">{connection.data?.data.reason||'등록된 미국 주식·ETF 코드와 기간을 입력합니다. 현재 수집 공급원은 FMP입니다.'}</p>
 <form className="grid gap-4 sm:grid-cols-3" onSubmit={async e=>{e.preventDefault();setError('');try{const result=await execute<{message:string}>('collect',{symbols:symbols.split(/[\s,]+/).filter(Boolean),start_date:start,end_date:end});setMessage(result.message)}catch(ex){setError(ex instanceof Error?ex.message:'수집 실패')}}}>
 <label className="text-xs">미국 종목 코드<input aria-label="수집 종목" required placeholder="AAPL, MSFT" className={inputClass+' mt-2'} value={symbols} onChange={e=>setSymbols(e.target.value)}/></label><label className="text-xs">시작일<input aria-label="수집 시작일" required type="date" className={inputClass+' mt-2'} value={start} onChange={e=>setStart(e.target.value)}/></label><label className="text-xs">종료일<input aria-label="수집 종료일" required type="date" className={inputClass+' mt-2'} value={end} onChange={e=>setEnd(e.target.value)}/></label><Button type="submit" tone="primary" disabled={!configured||s?.job.running} busy={pending.has('collect')}><Download size={15}/>FMP 가격 수집</Button></form>
 <div className="mt-4"><ErrorMessage message={error}/>{message&&<p className="text-sm text-emerald-700">{message}</p>}</div>
 </Panel>;
}
