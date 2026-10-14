import {useEffect,useRef,useState} from 'react';
import {request} from '../../../data/api';
import {Panel} from '../../../ui/Panel';
import {Button,ErrorMessage,inputClass} from '../../../ui/Primitives';
interface Project {input?:string;id:string;name:string;kind:string;artifact?:string;state:string;folder:string;created_at:string;original_files?:number;inferred_files?:number;unavailable?:number;limitations?:string[];error?:string;function_total?:number;decompiled_functions?:number;unavailable_functions?:number}
interface AnalysisStatus {active:boolean;stage:string;detail:string;project:Project|null}
export function ProgramAnalysis(){
 const [busy,setBusy]=useState(false),[web,setWeb]=useState(false),[url,setUrl]=useState(''),[target,setTarget]=useState(''),[error,setError]=useState(''),[result,setResult]=useState<Project|null>(null);
 const [progress,setProgress]=useState<AnalysisStatus|null>(null),[selecting,setSelecting]=useState(false);
 const pending=useRef(false),revision=useRef(0),seen=useRef('');
 useEffect(()=>{
  let disposed=false,running=false;let timer:ReturnType<typeof setTimeout>;
  const poll=async()=>{
   const current=revision.current;
   try{
    const next=await request<AnalysisStatus>('rea/status',{},'GET');
    if(disposed)return;
    running=next.active;
    if(current===revision.current){
     setProgress(old=>old?.active===next.active&&old.stage===next.stage&&old.detail===next.detail&&old.project?.id===next.project?.id?old:next);
     if(!pending.current){
      if(next.project){setTarget(next.project.input??'');if(next.active)setResult(null);else if(seen.current!==next.project.id){seen.current=next.project.id;setResult(next.project);setError(next.project.error??'');}}
      else if(next.stage==='failed'&&next.detail)setError(next.detail);
     }
    }
   }catch(e){if(!disposed)setError(e instanceof Error?e.message:'분석 상태 조회 실패');}
   if(!disposed&&(running||pending.current))timer=setTimeout(()=>void poll(),1000);
  };
  void poll();return()=>{disposed=true;clearTimeout(timer)};
 },[busy]);
 const working=busy||!!progress?.active;
 const analyze=async(kind:string,path:string)=>{
  pending.current=true;revision.current++;setBusy(true);setSelecting(false);setError('');setResult(null);setTarget(path);
  try{const saved=await request<Project>('rea/analyze',{kind,target:path});seen.current=saved.id;setResult(saved);setProgress({active:false,stage:saved.state,detail:'로컬 프로젝트 저장을 완료했습니다.',project:saved});}
  catch(e){setError(e instanceof Error?e.message:'분석 실패');try{const next=await request<AnalysisStatus>('rea/status',{},'GET');setProgress(next);if(next.project?.input===path){seen.current=next.project.id;setResult(next.project);}}catch{}}
  finally{pending.current=false;revision.current++;setBusy(false)}
 };
 const pick=async(kind:'file'|'folder')=>{pending.current=true;revision.current++;setSelecting(true);setWeb(false);setBusy(true);setError('');try{const selected=await request<{path:string}>('rea/pick',{kind});if(selected.path)await analyze(kind,selected.path);}catch(e){setError(e instanceof Error?e.message:'선택 실패')}finally{pending.current=false;revision.current++;setSelecting(false);setBusy(false)}};
 const open=async(id:string)=>{try{await request('rea/project/open',{id});}catch(e){setError(e instanceof Error?e.message:'폴더 열기 실패')}};
 const stop=async()=>{try{await request('rea/stop',{});}catch(e){setError(e instanceof Error?e.message:'중지 실패')}};
 return <div className="space-y-5"><Panel title="대상을 선택하면 소스와 분석 자료를 저장합니다." description="원본 파일·코드와 추론 결과를 분리해 로컬 프로젝트 폴더로 정리합니다.">
 <div className="grid gap-3 sm:grid-cols-3"><Button tone="primary" disabled={working} onClick={()=>void pick('file')}>파일 선택</Button><Button tone="primary" disabled={working} onClick={()=>void pick('folder')}>폴더 선택</Button><Button tone="primary" disabled={working} onClick={()=>setWeb(!web)}>웹사이트 분석</Button></div>
 {web&&<form className="mt-4 flex gap-2" onSubmit={e=>{e.preventDefault();void analyze('web',url.trim());}}><input type="url" required aria-label="분석할 웹사이트 주소" className={inputClass} value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://..." disabled={working}/><Button type="submit" busy={working} disabled={working}>소스 추출</Button></form>}
 <p className="mt-4 text-xs leading-6 text-slate-500">파일: EXE/DLL·ASAR·소스·패키지 / 폴더: 원문 코드와 모듈 구조 / 웹: 브라우저에 전달된 프론트엔드. 서버 내부 코드는 복원하지 않습니다.</p>
 {working&&<div className="mt-4 flex items-center gap-3"><span role="status" className="text-sm text-blue-700">{selecting?'파일·폴더 선택창에서 대상을 선택하세요.':progress?.active?progress.detail:'분석 요청을 처리하고 있습니다.'}</span><Button onClick={()=>void stop()}>{selecting||progress?.stage==='picking'?'선택 취소':'분석 중지'}</Button></div>}
 {target&&<p className="mt-3 break-all text-xs text-slate-500">{target}</p>}<ErrorMessage message={error}/>
 </Panel>{result&&<Panel title={result.state==='saved'?'로컬 폴더에 저장했습니다.':'분석 완료를 확인하지 못했습니다. 저장 자료를 확인하세요.'}><p className="text-sm font-medium">{result.name} · {result.artifact??result.kind}</p><p className="my-3 break-all text-xs text-slate-500">{result.folder}</p><p className="mb-3 text-xs text-slate-600">원본 파일 {result.original_files??0}개 · 추론 파일 {result.inferred_files??0}개</p>{result.function_total!=null&&<p className="mb-3 text-xs text-slate-600">함수 {result.function_total}개 · 의사코드 복원 {result.decompiled_functions??0}개 · 복원 불가 {result.unavailable_functions??0}개</p>}<div className="flex flex-wrap gap-3"><Button tone="primary" onClick={()=>void open(result.id)}>저장 폴더 열기</Button><a className="self-center text-sm text-blue-700" href={'#rea/project_explorer?id='+result.id}>프로젝트 탐색</a></div><p className="mt-4 text-xs text-slate-500">original/ 원본 추출 · inferred/ 추론 · analysis/ 구조와 출처</p>{result.limitations?.length&&<details className="mt-3 text-xs text-slate-500"><summary>분석 범위와 한계</summary><p className="mt-2 whitespace-pre-wrap">{result.limitations.join('\n')}</p></details>}</Panel>}</div>;
}
