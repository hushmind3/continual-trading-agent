import {FrameworkResult} from './FrameworkResult';
import {useEffect,useState} from 'react';
import {useOperations} from '../data/Operations';
import {useEndpoint} from '../data/useEndpoint';
import {Panel} from '../ui/Panel';
import {Button,ErrorMessage,inputClass} from '../ui/Primitives';
interface Action {id:string;name:string;menu:string;module:string;function:string;fields:string[];defaults?:Record<string,string|number>;api:string;stop_api:string}
const labels:Record<string,string>={mode:'FinRL 원형 모드 · train / test / trade',data_dir:'공식 OHLCV CSV 폴더 · 비워두면 원형 경로',currency:'통화',symbols:'종목 · 쉼표로 구분',symbol:'종목',start_date:'시작일',end_date:'종료일',exchange:'공식 거래소 코드',source:'기존 가격 CSV 경로',fundamentals:'기존 재무 CSV 경로',target_period:'예측 기간 · 비워두면 공식 기본값',config_path:'기존 Adaptive Rotation YAML · 비워두면 공식 제공 파일',as_of_date:'기준일',prediction_mode:'예측 방식 · single / rolling',weight_method:'비중 방식 · equal / min_variance'};
export function FrameworkTools({menu}:{menu:string}){
 const {state,execute,pending}=useOperations(),catalog=useEndpoint<{actions:Action[]}>('framework');
 const [selected,setSelected]=useState(''),[values,setValues]=useState<Record<string,string>>({}),[error,setError]=useState('');
 const actions=catalog.data?.actions.filter(a=>a.menu===menu)??[],action=actions.find(a=>a.id===selected)??actions[0];
 useEffect(()=>{if(state?.job.command==='framework'&&state.job.status==='succeeded')void catalog.refresh()},[state?.job.id,state?.job.status]);
 if(!actions.length)return <ErrorMessage message={catalog.error}/>;
 const run=async()=>{if(!action)return;setError('');const parameters:Record<string,unknown>={};for(const key of action.fields){const value=String(values[key]??action.defaults?.[key]??'').trim();if(value)parameters[key]=key==='symbols'?value.split(',').map(v=>v.trim()).filter(Boolean):value}try{await execute('framework/'+action.id,parameters)}catch(e){setError(e instanceof Error?e.message:'실행 실패')}};
 const job=state?.job.command==='framework'&&actions.some(a=>a.id===state.job.action)?state.job:null;
 return <Panel title={{workflows:'공식 시스템 원형 실행',markets:'공식 데이터·전처리',portfolio:'공식 전략·성과',connection:'공식 설정 검사'}[menu]??'공식 프레임워크 기능'}>
  <div className="flex flex-wrap items-center gap-3"><select aria-label="공식 기능 선택" className={inputClass} value={action?.id??''} onChange={e=>{setSelected(e.target.value);setError('')}}>{actions.map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</select><Button tone="primary" disabled={state?.job.running} busy={pending.has('framework/'+action?.id)} onClick={()=>void run()}>실행</Button><Button tone="danger" disabled={!job?.running} onClick={()=>void execute('stop',{}).catch(e=>setError(String(e)))}>작업 중지</Button></div>
  <div className="my-4 grid gap-3 sm:grid-cols-2">{action?.fields.map(key=><label key={key} className="text-xs text-slate-500">{labels[key]??key}{key==='currency'?<select className={inputClass+' mt-2'} value={values[key]??String(action.defaults?.[key]??'')} onChange={e=>setValues(v=>({...v,[key]:e.target.value}))}><option>USD</option><option>KRW</option></select>:<input className={inputClass+' mt-2'} type={key.endsWith('date')?'date':key==='total_timesteps'?'number':'text'} min={key==='total_timesteps'?1:undefined} value={values[key]??String(action.defaults?.[key]??'')} onChange={e=>setValues(v=>({...v,[key]:e.target.value}))}/>}</label>)}</div>
  <ErrorMessage message={error||catalog.error}/>
  {job&&<details open className="mt-4 text-xs text-slate-600"><summary>{job.action} · {job.running?'실행 중':job.status} · {job.finished_at??job.started_at}</summary><FrameworkResult job={job}/></details>}
 </Panel>;
}
