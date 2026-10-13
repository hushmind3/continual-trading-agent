import {useState} from 'react';
import {useOperations,useSystemState} from '../../data/Operations';
import {Panel,KeyValues} from '../../ui/Panel';
import {Button,ErrorMessage,inputClass} from '../../ui/Primitives';
interface Tool {name:string;description?:string;inputSchema:Record<string,unknown>;annotations?:{readOnlyHint?:boolean;destructiveHint?:boolean}}
interface ReaStatus {installed:boolean;version?:string;source:string;node_version?:string;tools:Tool[];tool_count?:number;reason?:string;session_connected?:boolean}
export function REAWorkspace(){
 const {execute,pending}=useOperations(),status=useSystemState<ReaStatus>('rea');
 const [selected,setSelected]=useState('analyze_javascript_application'),[query,setQuery]=useState(''),[argumentsJson,setArgumentsJson]=useState('{}'),[result,setResult]=useState<unknown>(null),[error,setError]=useState('');
 const data=status.data,tools=data?.tools??[],visible=tools.filter(t=>(t.name+' '+(t.description??'')).toLowerCase().includes(query.toLowerCase())),tool=tools.find(t=>t.name===selected)??tools[0];
 const run=async()=>{setError('');try{const argumentsValue=JSON.parse(argumentsJson);if(!argumentsValue||Array.isArray(argumentsValue)||typeof argumentsValue!=='object')throw new Error('도구 입력은 JSON 객체로 작성하세요.');setResult(await execute('rea/run',{tool:tool?.name,arguments:argumentsValue}));}catch(e){setError(e instanceof Error?e.message:'REA 실행 실패')}};
 const doctor=async()=>{setError('');try{setResult(await execute('rea/doctor',{}));}catch(e){setError(e instanceof Error?e.message:'환경 진단 실패')}};
 const stop=async()=>{try{const r=await execute('rea/stop',{});setResult(r);}catch(e){setError(e instanceof Error?e.message:'REA 중지 실패')}};
 return <div className="space-y-5"><Panel title="REA · Reverse Engineer Anything" description="공식 REA 도구로 바이너리·JavaScript·관리 코드·브라우저 동작을 분석합니다.">
 <KeyValues items={[["설치",data?.installed?'확인됨':'준비 필요'],['REA 버전',data?.version??'—'],['Node',data?.node_version??'—'],['원본 MCP 도구',String(data?.tool_count??0)]]}/>
 <a className="text-xs text-blue-700" href={data?.source??'https://github.com/morluto/rea'} target="_blank" rel="noreferrer">원본 GitHub</a>
 <ErrorMessage message={status.error||data?.reason||''}/><div className="mt-4 flex gap-2"><Button onClick={()=>void status.refresh()} busy={status.loading}>설치 확인</Button><Button onClick={()=>void doctor()} busy={pending.has('rea/doctor')} disabled={!data?.installed}>환경 진단</Button></div>
 <p className="mt-3 text-xs text-slate-500">심층 분석 엔진·플랫폼별 도구의 준비 여부는 원본 환경 진단 결과로 확인합니다.</p></Panel>
 <Panel title="원본 도구 실행" description="도구와 실제 입력을 직접 선택합니다. 분석 세션은 다음 호출에도 유지됩니다.">
 <input aria-label="REA 도구 검색" className={inputClass+' mb-3'} value={query} onChange={e=>setQuery(e.target.value)} placeholder="도구 이름·설명 검색"/>
 <select aria-label="REA 도구 선택" className={inputClass} value={tool?.name??''} onChange={e=>{setSelected(e.target.value);setArgumentsJson('{}');setResult(null)}}>{visible.map(t=><option key={t.name} value={t.name}>{t.name}</option>)}</select>
 <p className="my-3 text-xs text-slate-600">{tool?.description}</p><p className="text-xs text-slate-500">{tool?.annotations?.readOnlyHint?'읽기 도구':'원본 도구의 입력·대상 변경 조건을 확인하세요.'}</p>
 <details className="my-3 text-xs"><summary>원본 입력 스키마</summary><pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap">{JSON.stringify(tool?.inputSchema??{},null,2)}</pre></details>
 <label className="block text-xs">도구 입력 JSON<textarea aria-label="REA 도구 입력" className={inputClass+' mt-2 min-h-36 font-mono'} value={argumentsJson} onChange={e=>setArgumentsJson(e.target.value)}/></label>
 <div className="mt-3 flex gap-2"><Button tone="primary" onClick={()=>void run()} disabled={!data?.installed||!tool} busy={pending.has('rea/run')}>실행</Button><Button onClick={()=>void stop()} disabled={!pending.has('rea/run')}>분석 중지</Button></div><ErrorMessage message={error}/>
 </Panel>{result!==null&&<Panel title="REA 원본 결과"><pre className="max-h-[38rem] overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(result,null,2)}</pre></Panel>}</div>;
}
