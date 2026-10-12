import {useState} from 'react';
import {FrameworkTools} from './FrameworkTools';
import {NativeModuleRunner} from './NativeModuleRunner';
import {useSystemState} from '../data/Operations';
import {Panel,KeyValues} from '../ui/Panel';
import {Button,ErrorMessage,inputClass} from '../ui/Primitives';
import type {FrameworkScope} from '../data/types';
interface Module {id:string;path:string;framework:string;status:string;reason:string;description:string;functions:string[];signatures:Record<string,string>;dependencies:string[];calls:string[];actions:string[];verified_functions:string[];last_error?:string;native_api?:string}
export function ModuleCatalog({onRun,scope}:{onRun?:(module:string)=>void;scope?:FrameworkScope}={}){
 const catalog=useSystemState<{items:Module[];counts:Record<string,number>}>('framework');
 const [framework,setFramework]=useState('all'),[status,setStatus]=useState('all'),[query,setQuery]=useState('');
 const scoped=catalog.data?.items.filter(m=>!scope||m.framework===scope)??[];
 const items=scoped.filter(m=>(scope||framework==='all'||m.framework===framework)&&(status==='all'||m.status===status)&&(!query||(m.path+' '+m.functions.join(' ')).toLowerCase().includes(query.toLowerCase())));
 const owner=scope==='FinRL-X'?'FinRL-Trading':scope==='stockrl'?'프로젝트':scope;
 const counts=scope?scoped.reduce<Record<string,number>>((values,m)=>({...values,[m.status]:(values[m.status]??0)+1}),{}):catalog.data?.counts??{};
 return <Panel title={(owner?owner:'전체 공식')+' 모듈 · 연결·실행 상태'} description="실제 설치 소스의 함수·입력 계약·import·호출 관계. 정상 작동은 표시된 함수의 실제 성공 기록만 의미합니다." actions={<Button busy={catalog.loading} onClick={()=>void catalog.refresh()}>목록 갱신</Button>}>
  <ErrorMessage message={catalog.error}/><KeyValues items={Object.entries(counts).map(([k,v])=>[k,String(v)])}/>
  <div className="my-4 flex flex-wrap gap-3">{!scope&&<select className={inputClass} aria-label="프레임워크 필터" value={framework} onChange={e=>setFramework(e.target.value)}>{['all','FinRL','FinRL-X','stockrl'].map(v=><option key={v} value={v}>{v==='all'?'모든 프레임워크':v==='FinRL-X'?'FinRL-Trading (FinRL-X)':v}</option>)}</select>}<select className={inputClass} aria-label="모듈 상태 필터" value={status} onChange={e=>setStatus(e.target.value)}>{['all','연결·정상 작동','연결·실행 미확인','미연결','외부 인증 필요'].map(v=><option key={v} value={v}>{v==='all'?'모든 상태':v}</option>)}</select><input className={inputClass} aria-label="모듈·함수 검색" placeholder="모듈·함수 검색" value={query} onChange={e=>setQuery(e.target.value)}/></div>
  <p className="mb-3 text-xs text-slate-500">표시 {items.length}개</p>{items.map(m=><details key={m.id} className="border-b border-slate-100 py-3"><summary className="cursor-pointer text-xs font-medium text-blue-700">{m.path} · {m.status}</summary><p className="my-3 text-xs text-slate-500">{m.reason}</p>{m.last_error&&<ErrorMessage message={m.last_error}/>}<p className="text-xs text-emerald-700">실행 성공 함수: {m.verified_functions.join(', ')||'없음'}</p><div className="my-3">{m.native_api&&onRun&&<Button onClick={()=>onRun(m.id)}>원본 함수 실행으로 선택</Button>}</div><p className="my-3 text-xs text-slate-500">직접 실행: {m.actions.join(', ')||'호출하는 상위 기능의 내부 모듈'}</p><details className="text-xs text-slate-500"><summary>입력 계약 · 함수·클래스</summary><ul className="mt-3 space-y-2">{m.functions.map(f=><li key={f} className="break-all"><code>{f}({m.signatures[f]??''})</code></li>)}</ul></details><details className="mt-3 text-xs text-slate-500"><summary>의존성 · 호출 관계</summary><p className="mt-3">{m.dependencies.join(' → ')||'연결된 공식 모듈 의존성 없음'}</p><pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap">{m.calls.join('\n')}</pre></details></details>)}
 </Panel>;
}
export function FrameworkWorkspace({framework}:{framework?:FrameworkScope}={}){
 const [selected,setSelected]=useState('');
 return <div className="space-y-6">
  {framework==='FinRL'&&<p className="text-xs text-slate-600">FinRL · 기본 프레임워크 — SB3 알고리즘·공식 데이터 처리·학습·평가 기능</p>}
  {framework==='FinRL-X'&&<p className="text-xs text-slate-600">FinRL-Trading (FinRL-X) · 보조 프레임워크 — 추가 데이터·전략·비중 평가 기능. 알고리즘 선택·학습은 FinRL 구역에서 제공합니다.</p>}
  <ModuleCatalog scope={framework} onRun={setSelected}/>
  {['workflows','markets','portfolio','connection'].map(menu=><FrameworkTools key={menu} menu={menu} framework={framework}/>)}
  <NativeModuleRunner framework={framework} selectedModule={selected} onSelect={setSelected}/>
 </div>;
}
export function FinrlToolsWorkspace(){return <FrameworkWorkspace framework="FinRL"/>}
export function FinrlTradingWorkspace(){return <FrameworkWorkspace framework="FinRL-X"/>}
export function ProjectModulesWorkspace(){return <FrameworkWorkspace framework="stockrl"/>}
