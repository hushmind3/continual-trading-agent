import {useState} from 'react';
import {Play,Square} from 'lucide-react';
import {useOperations} from '../data/Operations';
import type {OperationProgress} from '../data/types';
import {Panel} from './Panel';
import {Button,ErrorMessage,Status,inputClass} from './Primitives';
const labels:Record<string,string>={pending:'대기',running:'진행',complete:'완료',failed:'실패',blocked:'보류'};
export function Progress({value}:{value:OperationProgress|undefined}){
 if(!value)return <p className="text-xs text-slate-400">실행 기록 없음</p>;
 return <div className="space-y-3"><Status tone={value.status==='failed'?'bad':value.status==='blocked'?'warn':value.status==='complete'?'good':'idle'}>{labels[value.status]||value.status}{value.applied?' · 코드 적용됨':''}</Status>
 {(value.detail||value.error)&&<p className="whitespace-pre-wrap text-xs text-amber-700">{value.detail||value.error}</p>}
 {[...value.stages,...(value.checks||[])].map(row=><div key={row.id} className="rounded-xl bg-slate-50 px-4 py-3"><div className="flex justify-between gap-3 text-sm"><b>{row.title}</b><Status tone={row.status==='failed'?'bad':row.status==='blocked'?'warn':row.status==='complete'?'good':'idle'}>{labels[row.status]}</Status></div>{row.detail&&<pre className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap break-all text-xs leading-5 text-slate-500">{row.detail}</pre>}{row.log_path&&<p className="mt-2 break-all text-xs text-slate-400">{row.log_path}</p>}{row.log&&<a className="mt-2 block text-xs text-blue-600" href="#finance/policy_learning">학습 로그: {row.log} →</a>}</div>)}
 {value.changed_files?.length? <details><summary className="cursor-pointer text-xs text-blue-600">변경 소스 {value.changed_files.length}개</summary><pre className="mt-2 max-h-40 overflow-auto text-xs text-slate-500">{value.changed_files.join('\n')}</pre></details>:null}</div>;
}
export function SystemControls(){
 const {state,execute,error:connection}=useOperations();const value=state?.automation;
 const [error,setError]=useState(''),[pending,setPending]=useState(''),[currency,setCurrency]=useState(()=>{const approved=Object.keys(state?.operations?.policies??{});return approved.length===1?approved[0]:'both'});
 async function command(name:string){setError('');setPending(name);try{await execute('system/'+name,name==='start'?{currencies:currency==='both'?['USD','KRW']:[currency]}:{});}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setPending('');}}
 const applying=value?.apply.status==='running';
 const controls=state?.operations?.controls,operating=Boolean(controls?.feed&&controls?.paper&&controls?.engine&&controls?.learning);
 const status=value?.system.active?'시작 중':operating?'운영 중':controls&&Object.values(controls).some(Boolean)?'일부 실행':'중지됨';
 return <Panel title="자동 운영" description="선택한 모델로 시세를 받고, 판단·가상매매·학습을 이어갑니다." className="operations-hero" collapsible={false} actions={<Status tone={value?.system.status==='failed'?'bad':value?.system.status==='blocked'?'warn':operating?'good':'idle'}>{status}</Status>}>
 <div className="operations-command-row"><div className="operations-command-actions"><select aria-label="자동 운영 통화" className={inputClass+' !w-auto'} value={currency} onChange={e=>setCurrency(e.target.value)}><option value="both">KRW + USD</option><option value="KRW">KRW</option><option value="USD">USD</option></select><Button tone="primary" disabled={applying} busy={pending==='start'||value?.system.active} onClick={()=>void command('start')}><Play size={14}/>자동 운영 시작</Button><Button tone="danger" busy={pending==='stop'} onClick={()=>void command('stop')}><Square size={13}/>운영 중지</Button></div></div>
 <div className="mt-4"><ErrorMessage message={error}/>{connection&&<p className="mt-2 text-xs text-amber-700">{connection} · 마지막 진행 상태를 유지하며 관리 API 재연결을 기다립니다.</p>}</div>
 {(value?.system.status==='failed'||value?.system.status==='blocked')&&(value.system.detail||value.system.error)&&<p className="mt-2 whitespace-pre-wrap text-xs text-amber-700">{value.system.detail||value.system.error}</p>}
 <div className="operations-hero-status"><details className="w-full"><summary className="operations-detail-summary">실행 단계와 상세 상태</summary><p className="my-3 text-xs leading-5 text-slate-500">선택 통화의 정책 준비 → 시세 수신 → 선택 정책 판단·가상매매·지속학습. 호환 정책이 없으면 정책 학습 후 직접 승인하세요.</p><Progress value={value?.system}/></details></div>
 </Panel>;
}
