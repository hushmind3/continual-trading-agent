import {FrameworkResult} from './FrameworkResult';
import {useState} from 'react';
import {useSystemState,useOperations} from '../../data/Operations';
import {Panel} from '../../ui/Panel';
import {Button,ErrorMessage,inputClass} from '../../ui/Primitives';
import type {FrameworkScope} from '../../data/types';
interface Action {id:string;name:string;menu:string;module:string;function:string;fields:string[];defaults?:Record<string,string|number>;api:string;stop_api:string}
const labels:Record<string,string>={data_dir:'공식 OHLCV CSV 폴더 · 비워두면 원형 경로',symbols:'종목 · 쉼표로 구분',start_date:'시작일',end_date:'종료일',exchange:'공식 거래소 코드',source:'기존 가격 CSV 경로',config_path:'기존 Adaptive Rotation YAML · 비워두면 공식 제공 파일',as_of_date:'기준일',};
export function FrameworkTools({menu,framework,actionId}:{menu:string;framework?:FrameworkScope;actionId?:string}){
 const {state,execute,pending}=useOperations(),catalog=useSystemState<{actions:Action[]}>('framework');
 const [selected,setSelected]=useState(''),[values,setValues]=useState<Record<string,string>>({}),[error,setError]=useState('');
 const actions=catalog.data?.actions.filter(a=>a.menu===menu&&(!framework||a.module.startsWith(framework+':'))&&(!actionId||a.id===actionId))??[],action=actions.find(a=>a.id===selected)??actions[0];
 if(!actions.length)return <ErrorMessage message={catalog.error}/>;
 const run=async()=>{if(!action)return;setError('');const parameters:Record<string,unknown>={};for(const key of action.fields){const value=String(values[key]??action.defaults?.[key]??'').trim();if(value)parameters[key]=key==='symbols'?value.split(',').map(v=>v.trim()).filter(Boolean):value}try{await execute('framework/'+action.id,parameters)}catch(e){setError(e instanceof Error?e.message:'실행 실패')}};
 const job=state?.job.command==='framework'&&actions.some(a=>a.id===state.job.action)?state.job:null;
 const owner=framework==='FinRL-X'?'FinRL-Trading':framework;
 return <Panel title={(owner?owner+' · ':'')+({workflows:'시스템 실행',markets:'데이터·전처리',connection:'설정 검사'}[menu]??'공식 프레임워크 기능')}>
  <p className="mb-3 text-xs text-slate-600">{action?.name} · {action?.module} · {action?.function}</p>
  <div className="flex flex-wrap items-center gap-3"><select aria-label="공식 기능 선택" className={inputClass} value={action?.id??''} onChange={e=>{setSelected(e.target.value);setError('')}}>{actions.map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</select><Button tone="primary" disabled={state?.job.running} busy={pending.has('framework/'+action?.id)} onClick={()=>void run()}>실행</Button></div>
  <div className="my-4 grid gap-3 sm:grid-cols-2">{action?.fields.map(key=><label key={key} className="text-xs text-slate-500">{labels[key]??key}{<input className={inputClass+' mt-2'} type={key.endsWith('date')?'date':key==='total_timesteps'?'number':'text'} min={key==='total_timesteps'?1:undefined} value={values[key]??String(action.defaults?.[key]??'')} onChange={e=>setValues(v=>({...v,[key]:e.target.value}))}/>}</label>)}</div>
  <ErrorMessage message={error||catalog.error}/>
  {job&&<details open className="mt-4 text-xs text-slate-600"><summary>{job.action} · {job.running?'실행 중':job.status} · {job.finished_at??job.started_at}</summary><FrameworkResult job={job}/></details>}
 </Panel>;
}
