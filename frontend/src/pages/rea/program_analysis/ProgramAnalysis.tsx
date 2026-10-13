import {useState} from 'react';
import {request} from '../../../data/api';
import {Panel} from '../../../ui/Panel';
import {Button,ErrorMessage,inputClass} from '../../../ui/Primitives';
interface Project {id:string;name:string;kind:string;artifact?:string;state:string;folder:string;created_at:string;original_files?:number;inferred_files?:number;unavailable?:number;limitations?:string[];error?:string}
export function ProgramAnalysis(){
 const [busy,setBusy]=useState(false),[web,setWeb]=useState(false),[url,setUrl]=useState(''),[target,setTarget]=useState(''),[error,setError]=useState(''),[result,setResult]=useState<Project|null>(null);
 const analyze=async(kind:string,path:string)=>{setBusy(true);setError('');setResult(null);setTarget(path);try{setResult(await request<Project>('rea/analyze',{kind,target:path}));}catch(e){setError(e instanceof Error?e.message:'분석 실패')}finally{setBusy(false)}};
 const pick=async(kind:'file'|'folder')=>{setWeb(false);setBusy(true);setError('');try{const selected=await request<{path:string}>('rea/pick',{kind});if(selected.path)await analyze(kind,selected.path);}catch(e){setError(e instanceof Error?e.message:'선택 실패')}finally{setBusy(false)}};
 const open=async(id:string)=>{try{await request('rea/project/open',{id});}catch(e){setError(e instanceof Error?e.message:'폴더 열기 실패')}};
 const stop=async()=>{try{await request('rea/stop',{});}catch(e){setError(e instanceof Error?e.message:'중지 실패')}};
 return <div className="space-y-5"><Panel title="대상을 선택하면 소스와 분석 자료를 저장합니다." description="원본 파일·코드와 추론 결과를 분리해 로컬 프로젝트 폴더로 정리합니다.">
 <div className="grid gap-3 sm:grid-cols-3"><Button tone="primary" disabled={busy} onClick={()=>void pick('file')}>파일 선택</Button><Button tone="primary" disabled={busy} onClick={()=>void pick('folder')}>폴더 선택</Button><Button tone="primary" disabled={busy} onClick={()=>setWeb(!web)}>웹사이트 분석</Button></div>
 {web&&<form className="mt-4 flex gap-2" onSubmit={e=>{e.preventDefault();void analyze('web',url.trim());}}><input type="url" required aria-label="분석할 웹사이트 주소" className={inputClass} value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://..." disabled={busy}/><Button type="submit" busy={busy} disabled={busy}>소스 추출</Button></form>}
 <p className="mt-4 text-xs leading-6 text-slate-500">파일: EXE/DLL·ASAR·소스·패키지 / 폴더: 원문 코드와 모듈 구조 / 웹: 브라우저에 전달된 프론트엔드. 서버 내부 코드는 복원하지 않습니다.</p>
 {busy&&<div className="mt-4 flex items-center gap-3"><span role="status" className="text-sm text-blue-700">선택·분석·저장 중…</span><Button onClick={()=>void stop()}>분석 중지</Button></div>}
 {target&&<p className="mt-3 break-all text-xs text-slate-500">{target}</p>}<ErrorMessage message={error}/>
 </Panel>{result&&<Panel title="로컬 폴더에 저장했습니다."><p className="text-sm font-medium">{result.name} · {result.artifact??result.kind}</p><p className="my-3 break-all text-xs text-slate-500">{result.folder}</p><div className="flex flex-wrap gap-3"><Button tone="primary" onClick={()=>void open(result.id)}>저장 폴더 열기</Button><a className="self-center text-sm text-blue-700" href={'#rea/project_explorer?id='+result.id}>프로젝트 탐색</a></div><p className="mt-4 text-xs text-slate-500">original/ 원본 추출 · inferred/ 추론 · analysis/ 구조와 출처</p>{result.limitations?.length&&<details className="mt-3 text-xs text-slate-500"><summary>분석 범위와 한계</summary><p className="mt-2 whitespace-pre-wrap">{result.limitations.join('\n')}</p></details>}</Panel>}</div>;
}
