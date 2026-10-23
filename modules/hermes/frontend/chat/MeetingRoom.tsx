import {useEffect,useLayoutEffect,useRef,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,Select,ErrorMessage} from '@platform/ui/Primitives';
import {ArrowLeft,Square,MessageCircle} from 'lucide-react';
import {MarkdownContent} from '@platform/ui/MarkdownContent';
import {failure,prefix,working,type AgentStatus} from '../types';
import {displayEngineResponse} from './EngineNotes';

type Speech={id?:string;staff_id?:string;actor?:string;name?:string;statement?:string;content?:string;status?:string;error?:string;source?:string;source_session_id?:string;reply_to?:string};
type Meeting={id:string;topic:string;status:string;created_at:string;summary?:string;venture_id?:string;minutes?:Speech[]};
type Staff={staff_id:string;name:string;title:string;description:string};
type Room={session_id:string;meetings:Meeting[];staff:Staff[];manager_staff_id?:string;ventures?:{id:string;status:string}[]};
type Company={id:string;title:string};
const label=(value:string)=>({running:'토론 중',completed:'토론 완료',failed:'토론 중단',paused:'보류',stopped:'중지'}[value]||value);

export function MeetingRoom({companies,onTalk,onReview,engineStatus}:{companies:Company[];onTalk:(id:string)=>void;onReview:(id:string)=>void;engineStatus?:AgentStatus}){
 const preferred=engineStatus?.job.meeting;
 const [company,setCompany]=useState(preferred?.company_id||companies[0]?.id||''),[room,setRoom]=useState<Room>(),[meetingId,setMeetingId]=useState(preferred?.id||''),[role,setRole]=useState('all'),[error,setError]=useState('');
 const thread=useRef<HTMLDivElement>(null),follow=useRef(true);
 useEffect(()=>{if(!companies.some(item=>item.id===company))setCompany(companies[0]?.id||'')},[companies,company]);
 useEffect(()=>{if(preferred?.id){setCompany(preferred.company_id);setMeetingId(preferred.id);setRole('all');follow.current=true}},[preferred?.id,preferred?.run_id,preferred?.company_id]);
 useEffect(()=>{if(!company)return;let live=true;let timer:ReturnType<typeof setTimeout>;
  setRoom(undefined);setError('');const refresh=async()=>{try{const next=await request<Room>('projects/conversation',{id:company,action:'meetings'});if(live){setRoom(next);setError('')}}catch(e){if(live)setError(failure(e))}finally{if(live)timer=setTimeout(()=>void refresh(),1200)}};
  void refresh();return()=>{live=false;clearTimeout(timer)};
 },[company]);
 const meetings=room?.meetings??[],selected=meetings.find(item=>item.id===meetingId)??meetings[0],staff=room?.staff??[];
 const live=preferred?.id===selected?.id?preferred:undefined;
 const speeches=[...(selected?.minutes??[])];
 if(live?.turn_id&&live.status==='running'){const i=speeches.findIndex(item=>item.id===live.turn_id);const turn={...(i<0?{}:speeches[i]),id:live.turn_id,staff_id:live.staff_id,name:staff.find(item=>item.staff_id===live.staff_id)?.title,statement:live.text??'',status:live.turn_status,source:'hermes_delegate',source_session_id:live.source_session_id};if(i<0)speeches.push(turn);else speeches[i]=turn}
 const staffSpeeches=speeches.filter(item=>item.actor!=='owner'),shown=role==='all'?staffSpeeches:staffSpeeches.filter(item=>item.staff_id===role),status=engineStatus?.job.session_id===room?.session_id?engineStatus:undefined,active=working(status),state=live?.status||selected?.status||'';
 useLayoutEffect(()=>{if(follow.current&&thread.current)thread.current.scrollTop=thread.current.scrollHeight},[JSON.stringify(shown)]);
 return <section className="ha-discussion-room" aria-label="회의실">
  <header className="ha-discussion-heading"><div className="min-w-0"><h2><MessageCircle size={20}/>회의</h2><p className="truncate" title={selected?.topic}>{selected?.topic||(preferred?.topic||'새 회의가 시작되면 여기에 표시됩니다.')}</p></div><div className="flex shrink-0 items-center gap-2">{state&&<span className="ha-meeting-badge">{label(state)}</span>}<Button variant="ghost" onClick={()=>onTalk(company)}><ArrowLeft size={15}/>총괄 대화</Button></div></header>
  <div className="ha-discussion-toolbar">{companies.length>1&&<Select aria-label="회의 조직" value={company} onChange={event=>{setCompany(event.target.value);setMeetingId('')}}>{companies.map(item=><option key={item.id} value={item.id}>{item.title}</option>)}</Select>}{meetings.length>1&&<Select aria-label="회의 안건" value={selected?.id||''} onChange={event=>{setMeetingId(event.target.value);setRole('all');follow.current=true}}>{meetings.map(item=><option key={item.id} value={item.id}>{item.topic} · {label(item.status)}</option>)}</Select>}<nav aria-label="회의 직군"><Button variant="ghost" tone={role==='all'?'primary':'neutral'} onClick={()=>setRole('all')}>전체</Button>{staff.map(person=><Button key={person.staff_id} variant="ghost" tone={role===person.staff_id?'primary':'neutral'} aria-label={person.name} title={person.description} onClick={()=>setRole(person.staff_id)}>{person.name}</Button>)}</nav></div>
  {error&&<ErrorMessage message={error}/>}
  <div ref={thread} className="ha-discussion-thread" aria-live="polite" onScroll={()=>{const el=thread.current;if(el)follow.current=el.scrollHeight-el.scrollTop-el.clientHeight<90}}>
   {!room&&!error&&<p className="ha-discussion-empty">회의에 연결하고 있습니다…</p>}
   {room&&!shown.length&&<p className="ha-discussion-empty">{state==='running'?'안건이 등록됐습니다. 첫 발언을 기다리고 있습니다…':'이 회의의 발언이 아직 없습니다.'}</p>}
   {shown.map((speech,index)=><article key={speech.id||selected?.id+'-'+index+'-'+speech.staff_id} className={'ha-discussion-line '+(speech.actor==='owner'?'is-owner':speech.source==='failure'?'is-failure':'')}><span className="ha-meeting-avatar">{speech.actor==='owner'?'대표':staff.find(person=>person.staff_id===speech.staff_id)?.name||'직원'}</span><div className="ha-discussion-message"><header><b>{speech.actor==='owner'?'대표':staff.find(person=>person.staff_id===speech.staff_id)?.name||speech.name||'직원'}</b>{speech.source==='hermes_delegate'&&<small>독립 검토</small>}{speech.status==='speaking'&&<small>답변 중…</small>}{speech.status==='failed'&&<small>발언 중단</small>}</header><div className="ha-discussion-bubble">{speech.statement||speech.content?<MarkdownContent text={displayEngineResponse(speech.statement||speech.content||'')}/>:<span className="ha-typing" aria-label="발언 준비 중">생각을 정리하고 있습니다…</span>}{speech.error&&<p className="mt-2 text-sm text-red-700">{displayEngineResponse(speech.error)}</p>}</div>{speech.source_session_id&&<details className="ha-discussion-source"><summary>발언 정보</summary><p>{staff.find(person=>person.staff_id===speech.staff_id)?.name||'직원'} · Hermes 원본 위임 세션</p><p className="break-all">{speech.source_session_id}</p>{speech.reply_to&&<p>검토 쟁점 · {speech.reply_to}</p>}</details>}</div></article>)}
   {selected?.summary&&!speeches.some(item=>item.source==='moderator'||item.source==='failure')&&<article className="ha-discussion-line"><span className="ha-meeting-avatar">{staff.find(person=>person.staff_id===room?.manager_staff_id)?.name||'총괄'}</span><div className="ha-discussion-message"><header><b>{staff.find(person=>person.staff_id===room?.manager_staff_id)?.name||'총괄'} · 저장된 결론</b></header><div className="ha-discussion-bubble"><MarkdownContent text={selected.summary}/></div></div></article>}
   {live?.error&&!speeches.some(item=>item.source==='failure')&&<p className="ha-discussion-empty text-red-700">{displayEngineResponse(live.error)}</p>}
   {selected?.venture_id&&room?.ventures?.some(item=>item.id===selected.venture_id&&item.status==='pending')&&<div className="ha-discussion-proposal"><b>승인 대기 초안이 제출됐습니다.</b><p>총괄 대화의 사업관리에서 검토·수정·승인할 수 있습니다. 아직 실행하지 않습니다.</p><Button onClick={()=>onReview(company)}>사업 초안 검토</Button></div>}
  </div>
  <footer className="ha-discussion-toolbar"><p className="min-w-0 flex-1 text-sm text-slate-500">{state==='running'?'총괄이 직원들과 토론 중입니다. 마치면 총괄 대화에 요약 보고합니다.':'회의는 직원들이 진행합니다. 보고 검토와 수정 지시는 총괄 대화에서 하세요.'}</p>{active&&<Button tone="danger" aria-label="회의 실행 중지" onClick={()=>void request(prefix+'stop',{}).catch(e=>setError(failure(e)))}><Square size={14}/></Button>}<Button variant="ghost" onClick={()=>onTalk(company)}>{state==='running'?'총괄에게 지시':'총괄 보고 보기'}</Button></footer>
 </section>;
}
