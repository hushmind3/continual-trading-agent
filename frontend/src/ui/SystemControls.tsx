import {useEffect,useState} from 'react';
import {useOperations} from '../data/Operations';
import {request} from '../data/api';
import type {AutomationState,OperationProgress} from '../data/types';
import {Panel} from './Panel';
import {Button,ErrorMessage,Status,inputClass} from './Primitives';
const labels:Record<string,string>={pending:'대기',running:'진행',complete:'완료',failed:'실패',blocked:'보류'};
function Progress({value}:{value:OperationProgress|undefined}){
 if(!value)return <p className="text-xs text-slate-400">실행 기록 없음</p>;
 return <div className="space-y-3"><Status tone={value.status==='failed'?'bad':value.status==='blocked'?'warn':value.status==='complete'?'good':'idle'}>{labels[value.status]||value.status}{value.applied?' · 코드 적용됨':''}</Status>
 {(value.detail||value.error)&&<p className="whitespace-pre-wrap text-xs text-amber-700">{value.detail||value.error}</p>}
 {[...value.stages,...(value.checks||[])].map(row=><div key={row.id} className="rounded-xl bg-slate-50 px-4 py-3"><div className="flex justify-between gap-3 text-sm"><b>{row.title}</b><Status tone={row.status==='failed'?'bad':row.status==='blocked'?'warn':row.status==='complete'?'good':'idle'}>{labels[row.status]}</Status></div>{row.detail&&<pre className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap break-all text-xs leading-5 text-slate-500">{row.detail}</pre>}{row.log_path&&<p className="mt-2 break-all text-xs text-slate-400">{row.log_path}</p>}{row.log&&<a className="mt-2 block text-xs text-blue-600" href="#learning">학습 로그: {row.log} →</a>}</div>)}
 {value.changed_files?.length? <details><summary className="cursor-pointer text-xs text-blue-600">변경 소스 {value.changed_files.length}개</summary><pre className="mt-2 max-h-40 overflow-auto text-xs text-slate-500">{value.changed_files.join('\n')}</pre></details>:null}</div>;
}
export function SystemControls(){
 const {state,refresh}=useOperations();const [value,setValue]=useState<AutomationState|undefined>(state?.automation),[error,setError]=useState(''),[connection,setConnection]=useState(''),[pending,setPending]=useState(''),[currency,setCurrency]=useState('both');
 useEffect(()=>{let closed=false;let timer:ReturnType<typeof setTimeout>;const poll=async()=>{try{const next=await request<AutomationState>('system/status');if(!closed){setValue(next);setConnection('');}}catch(e){if(!closed)setConnection(e instanceof Error?e.message:'서버 갱신 중 연결 대기');}if(!closed)timer=setTimeout(poll,2000);};void poll();return()=>{closed=true;clearTimeout(timer);}},[]);
 async function command(name:string){setError('');setPending(name);try{await request('system/'+name,name==='start'?{currencies:currency==='both'?['USD','KRW']:[currency]}:{});setValue(await request<AutomationState>('system/status'));void refresh();}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setPending('');}}
 const applying=value?.apply.status==='running';
 return <Panel title="통합 운영 제어" description="변경 적용·점검과 실제 운영 시작은 별도 동작입니다. 기존 개별 제어도 계속 사용할 수 있습니다.">
 <div className="flex flex-wrap items-center gap-3"><Button tone="primary" busy={pending==='apply'||applying} onClick={()=>void command('apply')}>변경 적용 · 전체 점검</Button><select aria-label="통합 운영 통화" className={inputClass+' !w-auto'} value={currency} onChange={e=>setCurrency(e.target.value)}><option value="both">KRW + USD</option><option value="KRW">KRW</option><option value="USD">USD</option></select><Button tone="primary" disabled={applying} busy={pending==='start'||value?.system.active} onClick={()=>void command('start')}>전체 시스템 시작</Button><Button tone="danger" busy={pending==='stop'} onClick={()=>void command('stop')}>전체 시스템 중지</Button></div>
 <div className="mt-4"><ErrorMessage message={error}/>{connection&&<p className="mt-2 text-xs text-amber-700">{connection} · 마지막 진행 상태를 유지하며 관리 API 재연결을 기다립니다.</p>}</div>
 <div className="mt-5 grid items-start gap-6 xl:grid-cols-2"><section><h3 className="mb-3 text-sm font-bold">변경 적용 · 점검</h3><Progress value={value?.apply}/></section><section><h3 className="mb-3 text-sm font-bold">전체 시스템 운영</h3><Progress value={value?.system}/></section></div>
 </Panel>;
}
