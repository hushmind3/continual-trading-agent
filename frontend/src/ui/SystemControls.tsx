import {useState} from 'react';
import {Play,Square} from 'lucide-react';
import {useOperations} from '../data/Operations';
import type {OperationProgress} from '../data/types';
import {Button,ErrorMessage,Status} from './Primitives';
const labels:Record<string,string>={pending:'대기',running:'진행',complete:'완료',failed:'실패',blocked:'보류'};
export function Progress({value}:{value:OperationProgress|undefined}){
 if(!value)return <p className="text-xs text-slate-400">실행 기록 없음</p>;
 return <div className="space-y-3"><Status tone={value.status==='failed'?'bad':value.status==='blocked'?'warn':value.status==='complete'?'good':'idle'}>{labels[value.status]||value.status}{value.applied?' · 코드 적용됨':''}</Status>
 {(value.detail||value.error)&&<p className="whitespace-pre-wrap text-xs text-amber-700">{value.detail||value.error}</p>}
 {[...value.stages,...(value.checks||[])].map(row=><div key={row.id} className="rounded-xl bg-slate-50 px-4 py-3"><div className="flex justify-between gap-3 text-sm"><b>{row.title}</b><Status tone={row.status==='failed'?'bad':row.status==='blocked'?'warn':row.status==='complete'?'good':'idle'}>{labels[row.status]}</Status></div>{row.detail&&<pre className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap break-all text-xs leading-5 text-slate-500">{row.detail}</pre>}{row.log_path&&<p className="mt-2 break-all text-xs text-slate-400">{row.log_path}</p>}{row.log&&<a className="mt-2 block text-xs text-blue-600" href="#finance/policy_learning">학습 로그: {row.log} →</a>}</div>)}
 {value.changed_files?.length? <details><summary className="cursor-pointer text-xs text-blue-600">변경 소스 {value.changed_files.length}개</summary><pre className="mt-2 max-h-40 overflow-auto text-xs text-slate-500">{value.changed_files.join('\n')}</pre></details>:null}</div>;
}
export function SystemControls(){
 const {state,execute,error:connection}=useOperations();
 const value=state?.automation,controls=state?.operations?.controls;
 const [error,setError]=useState(''),[pending,setPending]=useState(''),[currency,setCurrency]=useState(()=>{
  const approved=Object.keys(state?.operations?.policies??{});
  return approved.length===1?approved[0]:'both';
 });
 const operating=Boolean(controls?.feed&&controls?.paper&&controls?.engine&&controls?.learning);
 const partial=Boolean(controls&&Object.values(controls).some(Boolean));
 const starting=Boolean(value?.system.active),applying=value?.apply.status==='running';
 const problem=value?.system.status==='failed'||value?.system.status==='blocked';
 const status=starting?'시작 중':operating?'운영 중':partial?'일부 실행':'중지됨';
 const stateTone=problem?'error':starting||operating?'active':partial?'partial':'idle';
 async function command(name:'start'|'stop'){
  setError('');setPending(name);
  try{await execute('system/'+name,name==='start'?{currencies:currency==='both'?['USD','KRW']:[currency]}:{});}
  catch(e){setError(e instanceof Error?e.message:String(e));}
  finally{setPending('');}
 }
 return <section className="ops-command" aria-label="자동 운영">
  <div className="ops-command-head">
   <h2>자동 운영</h2>
   <span className="ops-command-status" data-state={stateTone} role="status">{status}</span>
  </div>
  <div className="ops-command-main">
   <div className="ops-command-caption">
    <strong>{operating?'시스템 가동 중':starting?'운영을 시작하고 있습니다':partial?'일부 기능이 실행 중입니다':'운영 준비'}</strong>
    <span>{currency==='both'?'국내 · 미국':currency==='KRW'?'국내':'미국'} 시장</span>
   </div>
   <div className="ops-command-actions">
    <label className="ops-currency">
     <span className="sr-only">자동 운영 통화</span>
     <select value={currency} onChange={e=>setCurrency(e.target.value)} aria-label="자동 운영 통화" disabled={pending!==''}>
      <option value="both">전체</option><option value="KRW">KRW</option><option value="USD">USD</option>
     </select>
    </label>
    <Button tone="primary" className="ops-start" disabled={applying||starting} busy={pending==='start'} onClick={()=>void command('start')}><Play size={15}/>시작</Button>
    <Button className="ops-stop" disabled={pending==='start'} busy={pending==='stop'} onClick={()=>void command('stop')}><Square size={13}/>중지</Button>
   </div>
  </div>
  {(error||connection||problem)&&<div className="ops-command-feedback" role="alert">
   <ErrorMessage message={error||''}/>
   {connection&&<p>{connection}</p>}
   {problem&&(value?.system.detail||value?.system.error)&&<p>{value.system.detail||value.system.error}</p>}
  </div>}
  <details className="ops-command-details">
   <summary>실행 내역</summary>
   <div className="ops-command-progress"><Progress value={value?.system}/></div>
  </details>
 </section>;
}
