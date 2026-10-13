import {FrameworkResult} from './FrameworkResult';
import {NativeParameterFields} from './NativeParameterFields';
import {useEffect,useMemo,useState} from 'react';
import {useSystemState,useOperations} from '../../../../data/Operations';
import {Panel} from '../../../../ui/Panel';
import {Button,ErrorMessage,inputClass} from '../../../../ui/Primitives';
import type {FrameworkScope} from '../../../../data/types';
interface Module {id:string;path:string;framework:string;functions:string[];signatures:Record<string,string>;parameters?:Record<string,{name:string;annotation?:string;required:boolean;default?:string}[]>;native_api?:string;status:string;reason:string}
export function NativeModuleRunner({selectedModule,onSelect,framework}:{selectedModule:string;onSelect:(module:string)=>void;framework?:FrameworkScope}){
 const catalog=useSystemState<{items:Module[]}>('framework'),{state,execute,pending}=useOperations();
 const [query,setQuery]=useState(''),[callable,setCallable]=useState(''),[kwargs,setKwargs]=useState('{}'),[init,setInit]=useState('{}'),[env,setEnv]=useState('{}'),[steps,setSteps]=useState('[]'),[argv,setArgv]=useState('[]'),[symbols,setSymbols]=useState(''),[source,setSource]=useState(''),[error,setError]=useState('');
 const modules=useMemo(()=>catalog.data?.items.filter(m=>m.native_api&&(!framework||m.framework===framework)&&(!query||(m.path+' '+m.functions.join(' ')).toLowerCase().includes(query.toLowerCase())))??[],[catalog.data,query,framework]);
 const module=modules.find(m=>m.id===selectedModule)??modules[0],functions=module?.functions.filter(name=>name.split('.').every(part=>!part.startsWith('_')))??[];
 const selected=functions.includes(callable)?callable:functions[0]??'';
 useEffect(()=>{setCallable('');setKwargs('{}');setInit('{}');setError('')},[selectedModule]);
 const signature=module?.signatures[selected]??module?.signatures[selected+'.__init__']??'';
 const parameters=module?.parameters?.[selected]??module?.parameters?.[selected+'.__init__']??[];
 const template=(fields:typeof parameters)=>Object.fromEntries(fields.filter(f=>f.required).map(f=>[f.name,f.annotation?.includes('DataFrame')?'$data':f.annotation?.includes('Series')?'$series':f.annotation?.includes('ndarray')?'$array':f.annotation&&/datetime|Timestamp|\bdate\b/.test(f.annotation)?{'$timestamp':''}:'']));
 const run=async()=>{setError('');try{const args=JSON.parse(kwargs),constructor=JSON.parse(init);for(const values of [args,constructor])for(const key of Object.keys(values))if(typeof values[key]==="string"&&/^[\[{]/.test(values[key]))values[key]=JSON.parse(values[key]);await execute('framework/native_call',{module:module?.id,callable:selected,kwargs:args,init_kwargs:constructor,env_kwargs:JSON.parse(env),steps:JSON.parse(steps),argv:JSON.parse(argv),symbols:symbols.split(',').map(s=>s.trim()).filter(Boolean),source})}catch(e){setError(e instanceof Error?e.message:'원본 함수 실행 실패')}};
 const jobFramework=catalog.data?.items.find(m=>m.id===state?.job?.parameters?.module)?.framework;
 const job=state?.job?.command==='framework'&&state.job.action==='native_call'&&(!framework||jobFramework===framework)?state.job:null;
 const owner=framework==='stockrl'?'프로젝트':framework;
 return <Panel title={(owner?owner+' · ':'')+'모듈 원본 함수 실행'} description="선택 구역의 공개 함수·클래스·메서드를 직접 호출합니다. 입력 인자와 필수 의존성은 기존 계약을 따릅니다.">
  <div className="grid gap-3 sm:grid-cols-2"><input className={inputClass} aria-label="원형 모듈 검색" placeholder="프레임워크·모듈·함수 검색" value={query} onChange={e=>setQuery(e.target.value)}/><select className={inputClass} aria-label="원형 모듈" value={module?.id??''} onChange={e=>onSelect(e.target.value)}>{modules.map(m=><option key={m.id} value={m.id}>{m.path} · {m.status}</option>)}</select><select className={inputClass} aria-label="원본 callable" value={selected} onChange={e=>setCallable(e.target.value)}>{functions.map(f=><option key={f}>{f}</option>)}</select><input className={inputClass} aria-label="원본 데이터 종목" placeholder="실제 저장 종목 · 쉼표로 구분" value={symbols} onChange={e=>setSymbols(e.target.value)}/></div>
  <p className="my-3 break-all text-xs text-blue-700">{selected}({signature})</p><p className="my-3 text-xs text-slate-500">{module?.reason}</p>
  <NativeParameterFields key={(module?.id??"")+selected} title="함수 입력값" parameters={parameters} value={kwargs} onChange={setKwargs}/>
  {selected.includes('.')&&<NativeParameterFields key={(module?.id??"")+selected+"-constructor"} title="클래스 생성자 입력값" parameters={module?.parameters?.[selected.split('.')[0]+'.__init__']??[]} value={init} onChange={setInit}/>}
  <div className="my-3 flex flex-wrap items-center gap-3"><Button onClick={()=>{setKwargs(JSON.stringify(template(parameters),null,2));if(selected.includes('.'))setInit(JSON.stringify(template(module?.parameters?.[selected.split('.')[0]+'.__init__']??[]),null,2))}}>원본 필수 인자 양식</Button><span className="text-xs text-slate-500">{parameters.map(p=>p.name+(p.required?' · 필수':' = '+p.default)).join(' / ')}</span></div>
  <label className="block text-xs text-slate-500">실제 입력 CSV 경로 · 비워두면 공식 DataStore 조회<input className={inputClass+' mt-2'} value={source} onChange={e=>setSource(e.target.value)}/></label>
  <div className="my-4 grid gap-3 sm:grid-cols-2"><label className="text-xs text-slate-500">함수 인자 JSON<textarea aria-label="원본 함수 인자" className={inputClass+' mt-2 min-h-32 font-mono'} value={kwargs} onChange={e=>setKwargs(e.target.value)}/></label><label className="text-xs text-slate-500">메서드 실행 시 클래스 생성자 인자 JSON<textarea aria-label="원본 생성자 인자" className={inputClass+' mt-2 min-h-32 font-mono'} value={init} onChange={e=>setInit(e.target.value)}/></label></div>
  <details className="mb-4 text-xs text-slate-500"><summary>$env를 사용하는 공식 환경 생성자 인자</summary><textarea aria-label="공식 환경 생성자 인자" className={inputClass+' mt-2 font-mono'} value={env} onChange={e=>setEnv(e.target.value)}/></details>
  <details className="mb-4 text-xs text-slate-500"><summary>원본 메서드 연결 · CLI 인자</summary><label className="mt-3 block">같은 인스턴스에서 호출할 메서드 배열 · save_as 결과는 $이름으로 다음 호출에 전달<textarea aria-label="원본 메서드 연결" className={inputClass+' mt-2 font-mono'} value={steps} onChange={e=>setSteps(e.target.value)}/></label><label className="mt-3 block">원본 argparse CLI 인자 배열<textarea aria-label="원본 CLI 인자" className={inputClass+' mt-2 font-mono'} value={argv} onChange={e=>setArgv(e.target.value)}/></label></details>
  <p className="mb-4 text-xs leading-6 text-slate-500">실제 데이터 참조: "$data" = 가격 DataFrame(tic), "$series" = 선택 종목 close Series, "$array" = 실제 숫자 배열, "$config" = FinRL 설정, "$indicators" = FinRL 기본 지표. "$initial_amount" = FinRL 설정 상수, "$price_data" = 종목별 실제 close Series, "$credential:FMP_API_KEY" 등은 보안 설정 참조입니다. 날짜·기간·Tensor 객체는 &#123;"$timestamp":"실제 날짜"&#125;, &#123;"$timedelta":&#123;"days":기간&#125;&#125;, &#123;"$tensor":"$array"&#125; 형식으로 전달합니다. 기본값을 사용하려면 해당 인자를 생략하세요. 인증 값은 기존 공급원 설정에서 준비하세요.</p>
  <div className="flex gap-3"><Button tone="primary" disabled={!selected||state?.job?.running} busy={pending.has('framework/native_call')} onClick={()=>void run()}>원본 함수 실행</Button></div><ErrorMessage message={error||catalog.error}/>
  {job&&<details open className="mt-4 text-xs text-slate-600"><summary>{job.running?'원본 실행 중':job.status} · {job.id}</summary><FrameworkResult job={job}/></details>}
 </Panel>;
}
