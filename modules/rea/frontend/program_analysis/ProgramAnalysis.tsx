import {useEffect,useRef,useState} from 'react';
import {request} from '@platform/data/api';
import {FileCode2,FolderOpen,Globe2,ArrowUpRight,FolderTree} from 'lucide-react';
import {Panel} from '@platform/ui/Panel';
import {Button,ErrorMessage,Status,Input} from '@platform/ui/Primitives';
interface Project {input?:string;id:string;name:string;kind:string;artifact?:string;state:string;folder:string;created_at:string;original_files?:number;inferred_files?:number;unavailable?:number;limitations?:string[];error?:string;function_total?:number;decompiled_functions?:number;unavailable_functions?:number}
interface AnalysisStatus {active:boolean;stage:string;detail:string;project:Project|null}
export function ProgramAnalysis(){
 const [busy,setBusy]=useState(false),[web,setWeb]=useState(false),[url,setUrl]=useState(''),[target,setTarget]=useState(''),[error,setError]=useState(''),[result,setResult]=useState<Project|null>(null);
 const [progress,setProgress]=useState<AnalysisStatus|null>(null),[selecting,setSelecting]=useState(false);
 const [opening,setOpening]=useState(false),[stopping,setStopping]=useState(false),[notice,setNotice]=useState('');
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
  pending.current=true;revision.current++;setBusy(true);setSelecting(false);setError('');setNotice('');setResult(null);setTarget(path);
  try{const saved=await request<Project>('rea/analyze',{kind,target:path});seen.current=saved.id;setResult(saved);setProgress({active:false,stage:saved.state,detail:'로컬 프로젝트 저장을 완료했습니다.',project:saved});}
  catch(e){setError(e instanceof Error?e.message:'분석 실패');try{const next=await request<AnalysisStatus>('rea/status',{},'GET');setProgress(next);if(next.project?.input===path){seen.current=next.project.id;setResult(next.project);}}catch{}}
  finally{pending.current=false;revision.current++;setBusy(false)}
 };
 const pick=async(kind:'file'|'folder')=>{pending.current=true;revision.current++;setSelecting(true);setWeb(false);setBusy(true);setError('');setNotice('');try{const selected=await request<{path:string}>('rea/pick',{kind});if(selected.path)await analyze(kind,selected.path);}catch(e){setError(e instanceof Error?e.message:'선택 실패')}finally{pending.current=false;revision.current++;setSelecting(false);setBusy(false)}};
 const open=async(id:string)=>{if(opening)return;setOpening(true);setError('');setNotice('');try{await request('rea/project/open',{id});setNotice('저장 폴더 열기를 요청했습니다. 파일 탐색기를 확인하세요.');}catch(e){setError(e instanceof Error?e.message:'폴더 열기 실패')}finally{setOpening(false)}};
 const stop=async()=>{if(stopping)return;setStopping(true);setError('');try{await request('rea/stop',{});setNotice('중지 요청을 전달했습니다.');}catch(e){setError(e instanceof Error?e.message:'중지 실패')}finally{setStopping(false)}};
 const resultLabel=result?.state==='saved'?'저장 완료':result?.state==='failed'?'분석 실패':['cancelled','canceled','stopped'].includes(result?.state??'')?'분석 중지':'분석 미완료';
 return <div className="rea-analysis-workspace space-y-6"><Panel title="분석 대상 선택" description="소스와 분석 자료를 실제 로컬 프로젝트 폴더에 저장합니다." className="rea-analysis-entry" collapsible={false}>
 <div className="rea-target-grid"><Button aria-label="파일 선택" className="rea-target-card" disabled={working} onClick={()=>void pick('file')}><FileCode2 size={25}/><b>파일 선택</b><span>EXE · DLL · ASAR<br/>소스 파일과 앱 패키지</span><ArrowUpRight size={15} className="rea-target-arrow"/></Button><Button aria-label="폴더 선택" className="rea-target-card" disabled={working} onClick={()=>void pick('folder')}><FolderOpen size={25}/><b>폴더 선택</b><span>프로젝트와 앱 폴더<br/>파일·모듈 구조 분석</span><ArrowUpRight size={15} className="rea-target-arrow"/></Button><Button aria-label="웹사이트 분석" aria-expanded={web} aria-controls="rea-website-form" className={'rea-target-card '+(web?'rea-target-selected':'')} disabled={working} onClick={()=>setWeb(!web)}><Globe2 size={25}/><b>웹사이트 분석</b><span>화면과 공개 스크립트<br/>브라우저로 전달된 코드</span><ArrowUpRight size={15} className="rea-target-arrow"/></Button></div>
 {web&&<form id="rea-website-form" className="rea-website-form" onSubmit={e=>{e.preventDefault();void analyze('web',url.trim());}}><label htmlFor="rea-analysis-url">웹사이트 주소</label><div><Input id="rea-analysis-url" type="url" pattern="https?://.+" title="http:// 또는 https://로 시작하는 주소를 입력하세요." required autoFocus aria-label="분석할 웹사이트 주소" value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://..." disabled={working}/><Button type="submit" tone="primary" busy={working} disabled={working}>소스 추출</Button></div></form>}
 <details className="rea-scope"><summary>대상별 추출 범위</summary><p>파일: EXE/DLL·ASAR·소스·패키지 / 폴더: 원문 코드와 모듈 구조 / 웹: 브라우저에 전달된 프론트엔드. 서버 내부 코드는 복원하지 않습니다.</p></details>
 {working&&<div className="rea-analysis-progress"><span role="status">{selecting?'파일·폴더 선택창에서 대상을 선택하세요.':progress?.active?progress.detail:'분석 요청을 처리하고 있습니다.'}</span><Button busy={stopping} disabled={stopping} onClick={()=>void stop()}>{selecting||progress?.stage==='picking'?'선택 취소':'분석 중지'}</Button></div>}
 {target&&<p className="rea-target-path">{target}</p>}<ErrorMessage message={error}/>{notice&&<p role="status" className="mt-3 text-sm text-slate-600">{notice}</p>}
 </Panel>{result&&<Panel title="분석 결과" className="rea-analysis-result" actions={<Status tone={result.state==='saved'?'good':'warn'}>{resultLabel}</Status>}>
 <div className="rea-result-heading"><span className="rea-result-icon"><FolderTree size={22}/></span><div><h3>{result.name}</h3><p>{result.artifact??result.kind}</p></div></div>
 {result.state!=='saved'&&<p className="mt-3 text-xs text-amber-700">분석 완료를 확인하지 못했습니다. 저장된 자료와 오류를 확인하세요.</p>}
 <div className="rea-result-metrics"><div><p>원본 파일</p><strong>{result.original_files??0}<span>개</span></strong></div><div><p>추론 파일</p><strong>{result.inferred_files??0}<span>개</span></strong></div>{result.function_total!=null&&<div><p>분석 함수</p><strong>{result.function_total}<span>개</span></strong></div>}</div>
 {result.function_total!=null&&<p className="mb-4 text-xs text-slate-500">의사코드 복원 {result.decompiled_functions??0}개 · 복원 불가 {result.unavailable_functions??0}개</p>}
 <p className="rea-saved-path">{result.folder}</p><div className="rea-result-actions"><Button tone="primary" busy={opening} disabled={opening} onClick={()=>void open(result.id)}><FolderOpen size={15}/>저장 폴더 열기</Button><a className="ui-button" href={'#rea/project_explorer?id='+encodeURIComponent(result.id)}>프로젝트 탐색 <ArrowUpRight size={14}/></a></div>
 <div className="rea-provenance"><span><code>original/</code> 원본 추출</span><span><code>inferred/</code> 추론</span><span><code>analysis/</code> 구조와 출처</span></div>
 {!!result.limitations?.length&&<details className="rea-scope"><summary>분석 범위와 한계</summary><p className="whitespace-pre-wrap">{result.limitations.join(String.fromCharCode(10))}</p></details>}
 </Panel>}</div>;
}
