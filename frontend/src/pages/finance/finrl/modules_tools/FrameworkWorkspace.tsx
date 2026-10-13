import {useState} from 'react';
import {NativeModuleRunner} from './NativeModuleRunner';
import {useSystemState} from '../../../../data/Operations';
import {Panel,KeyValues} from '../../../../ui/Panel';
import {Button,ErrorMessage,inputClass} from '../../../../ui/Primitives';
import type {FrameworkScope} from '../../../../data/types';
interface Module {id:string;path:string;framework:string;status:string;reason:string;description:string;functions:string[];signatures:Record<string,string>;dependencies:string[];calls:string[];actions:string[];verified_functions:string[];referenced:boolean;referenced_by:string[];entry_point:boolean;imported:boolean;import_status:string;import_error?:string;usage:string;execution_status:string;authentication_status:string;credential_inputs:string[];last_error?:string;native_api?:string}
export function ModuleCatalog({onRun,scope,scopes}:{onRun?:(module:string)=>void;scope?:FrameworkScope;scopes?:FrameworkScope[]}={}){
 const catalog=useSystemState<{items:Module[];counts:Record<string,number>}>('framework');
 const [framework,setFramework]=useState('all'),[status,setStatus]=useState('all'),[execution,setExecution]=useState('all'),[authentication,setAuthentication]=useState('all'),[query,setQuery]=useState('');
 const scoped=catalog.data?.items.filter(m=>(!scope||m.framework===scope)&&(!scopes||scopes.some(value=>value===m.framework)))??[];
 const items=scoped.filter(m=>(scope||framework==='all'||m.framework===framework)&&(status==='all'||m.status===status)&&(execution==='all'||m.execution_status===execution)&&(authentication==='all'||(authentication==='인증 입력 탐지'?m.credential_inputs?.length:!m.credential_inputs?.length))&&(!query||([m.path,m.status,m.reason,m.import_status,m.execution_status,m.authentication_status,...(m.credential_inputs??[]),...(m.referenced_by??[]),...m.functions].join(' ')).toLowerCase().includes(query.toLowerCase())));
 const owner=scope==='FinRL-X'?'FinRL-Trading':scope==='stockrl'?'프로젝트':scope??(scopes?'통합':undefined);
 const counts=scope||scopes?scoped.reduce<Record<string,number>>((values,m)=>({...values,[m.status]:(values[m.status]??0)+1}),{}):catalog.data?.counts??{};
 return <Panel title={(owner?owner:'전체')+' 모듈 · 사용 구분'} description="운영 코드 참조와 수동 실행 도구를 구분합니다. import·함수 실행·인증 상태는 각각 별도 표시합니다." actions={<Button busy={catalog.loading} onClick={()=>void catalog.refresh()}>목록 갱신</Button>}>
  <ErrorMessage message={catalog.error}/><KeyValues items={Object.entries(counts).map(([k,v])=>[k,String(v)])}/>
  <div className="my-4 flex flex-wrap gap-3">{!scope&&<select className={inputClass} aria-label="프레임워크 필터" value={framework} onChange={e=>setFramework(e.target.value)}>{(scopes?['all',...scopes]:['all','FinRL','FinRL-X','stockrl','REA','Platform']).map(v=><option key={v} value={v}>{v==='all'?'전체 모듈':v==='stockrl'?'프로젝트':v==='FinRL-X'?'FinRL-Trading (FinRL-X)':v}</option>)}</select>}
   <select className={inputClass} aria-label="모듈 사용 구분" value={status} onChange={e=>setStatus(e.target.value)}>{['all','운영 코드 참조','수동 실행 전용','참조 경로 없음','소스 해석 실패'].map(v=><option key={v} value={v}>{v==='all'?'모든 사용 구분':v}</option>)}</select>
   <select className={inputClass} aria-label="함수 실행 기록" value={execution} onChange={e=>setExecution(e.target.value)}>{['all','실행 성공 기록 있음','실행 기록 없음','최근 실행 실패'].map(v=><option key={v} value={v}>{v==='all'?'모든 실행 기록':v}</option>)}</select>
   <select className={inputClass} aria-label="소스 인증 입력" value={authentication} onChange={e=>setAuthentication(e.target.value)}>{['all','인증 입력 탐지','인증 입력 미탐지'].map(v=><option key={v} value={v}>{v==='all'?'모든 인증 입력':v}</option>)}</select>
   <input className={inputClass} aria-label="모듈·함수·상태 검색" placeholder="모듈·함수·상태 검색" value={query} onChange={e=>setQuery(e.target.value)}/></div>
  <p className="mb-3 text-xs text-slate-500">표시 {items.length}개</p>{items.map(m=><details key={m.id} className="border-b border-slate-100 py-3"><summary className="cursor-pointer text-xs font-medium text-blue-700">{m.path} · {m.status}</summary><p className="my-3 text-xs text-slate-500">{m.reason}</p>{m.import_error&&<ErrorMessage message={m.import_error}/>} {m.last_error&&<ErrorMessage message={m.last_error}/>}
   <p className="text-xs text-slate-500">import: {m.import_status} · 함수 실행: {m.execution_status}</p>
   <p className="mt-1 text-xs text-slate-500">인증: {m.authentication_status}</p>{!!m.credential_inputs?.length&&<p className="text-xs text-slate-500">소스의 인증 입력 이름: {m.credential_inputs.join(', ')}</p>}
   <p className="mt-1 text-xs text-slate-500">운영 참조 근거: {m.entry_point?'서버·CLI·작업 진입점':m.referenced_by?.join(', ')||'참조하는 운영 모듈 없음'}</p>
   <p className="text-xs text-emerald-700">실행 성공 기록이 있는 함수: {m.verified_functions.join(', ')||'없음'}</p><div className="my-3">{m.native_api&&onRun&&<Button onClick={()=>onRun(m.id)}>원본 함수 실행으로 선택</Button>}</div><p className="my-3 text-xs text-slate-500">실행 경로: {m.native_api?'사용자가 선택하는 framework/native_call':m.actions.join(', ')||(m.referenced?'상위 운영 코드의 내부 호출':'등록된 수동 실행 경로 없음')}</p><details className="text-xs text-slate-500"><summary>입력 계약 · 함수·클래스</summary><ul className="mt-3 space-y-2">{m.functions.map(f=><li key={f} className="break-all"><code>{f}({m.signatures[f]??''})</code></li>)}</ul></details><details className="mt-3 text-xs text-slate-500"><summary>의존성 · 호출 관계</summary><p className="mt-3">{m.dependencies.join(' → ')||'목록 내 모듈 의존성 없음'}</p><pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap">{m.calls.join('\n')}</pre></details></details>)}
 </Panel>;
}
export function FrameworkWorkspace({framework,scopes}:{framework?:FrameworkScope;scopes?:FrameworkScope[]}={}){
 const [selected,setSelected]=useState(()=>new URLSearchParams(location.hash.split('?')[1]??'').get('module')??'');
 return <div className="space-y-6">
  {framework==='FinRL'&&<p className="text-xs text-slate-600">FinRL · 기본 프레임워크 — SB3 알고리즘·공식 데이터 처리·학습·평가 기능</p>}
  <ModuleCatalog scope={framework} scopes={scopes} onRun={setSelected}/>
  {framework!=='stockrl'&&<NativeModuleRunner framework={scopes?'FinRL':framework} selectedModule={selected} onSelect={setSelected}/>}
  {(framework==='stockrl'||scopes?.includes('stockrl'))&&<Panel title="프로젝트 실행 API" description="프로젝트 모듈은 소속 작은 메뉴의 등록 API로 실행합니다."><a className="text-xs text-blue-700" href="#finance/all_backend_features?tab=commands">큰 메뉴 · 작은 메뉴별 API와 입력값 열기</a></Panel>}
 </div>;
}
