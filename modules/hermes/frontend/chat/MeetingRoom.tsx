import {useEffect,useLayoutEffect,useRef,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,Select,Textarea,ErrorMessage} from '@platform/ui/Primitives';
import {ArrowUp,ArrowLeft,Square,MessageCircle} from 'lucide-react';
import {MarkdownContent} from '@platform/ui/MarkdownContent';
import {failure,prefix,working,type AgentStatus} from '../types';
import {displayEngineResponse} from './EngineNotes';

type Speech={id?:string;role?:string;name?:string;statement?:string;content?:string;status?:string;error?:string;source?:string;source_session_id?:string;reply_to?:string};
type Meeting={id:string;topic:string;status:string;created_at:string;summary?:string;venture_id?:string;minutes?:Speech[]};
type Staff={role:string;name:string;title:string;description:string};
type Room={session_id:string;meetings:Meeting[];roles:Staff[];ventures?:{id:string;status:string}[]};
type Company={id:string;title:string};
const label=(value:string)=>({running:'토론 중',completed:'토론 완료',failed:'토론 중단',paused:'보류',stopped:'중지'}[value]||value);

export function MeetingRoom({companies,onTalk,onReview,engineStatus}:{companies:Company[];onTalk:(id:string)=>void;onReview:(id:string)=>void;engineStatus?:AgentStatus}){
 const preferred=engineStatus?.job.meeting;
 const [company,setCompany]=useState(preferred?.company_id||companies[0]?.id||''),[room,setRoom]=useState<Room>(),[meetingId,setMeetingId]=useState(preferred?.id||''),[role,setRole]=useState('all'),[message,setMessage]=useState(''),[pending,setPending]=useState(false),[error,setError]=useState('');
 const thread=useRef<HTMLDivElement>(null),follow=useRef(true);
 useEffect(()=>{if(!companies.some(item=>item.id===company))setCompany(companies[0]?.id||'')},[companies,company]);
 useEffect(()=>{if(preferred?.id){setCompany(preferred.company_id);setMeetingId(preferred.id);setRole('all');follow.current=true}},[preferred?.id,preferred?.run_id,preferred?.company_id]);
 useEffect(()=>{if(!company)return;let live=true;let timer:ReturnType<typeof setTimeout>;
  setRoom(undefined);setError('');const refresh=async()=>{try{const next=await request<Room>('projects/conversation',{id:company,action:'meetings'});if(live){setRoom(next);setError('')}}catch(e){if(live)setError(failure(e))}finally{if(live)timer=setTimeout(()=>void refresh(),1200)}};
  void refresh();return()=>{live=false;clearTimeout(timer)};
 },[company]);
 const meetings=room?.meetings??[],selected=meetings.find(item=>item.id===meetingId)??meetings[0],staff=room?.roles??[];
 const live=preferred?.id===selected?.id?preferred:undefined;
 const speeches=[...(selected?.minutes??[])];
 if(live?.turn_id&&live.status==='running'){const i=speeches.findIndex(item=>item.id===live.turn_id);const turn={...(i<0?{}:speeches[i]),id:live.turn_id,role:live.role,name:staff.find(item=>item.role===live.role)?.title,statement:live.text??'',status:live.turn_status,source:'hermes_delegate',source_session_id:live.source_session_id};if(i<0)speeches.push(turn);else speeches[i]=turn}
 const shown=role==='all'?speeches:speeches.filter(item=>item.role===role),status=engineStatus?.job.session_id===room?.session_id?engineStatus:undefined,active=working(status),state=live?.status||selected?.status||'';
 const draftKey='hermes.meeting-draft:'+company+':'+(selected?.id||'');
 useEffect(()=>{setMessage(localStorage.getItem(draftKey)||'')},[draftKey]);
 useLayoutEffect(()=>{if(follow.current&&thread.current)thread.current.scrollTop=thread.current.scrollHeight},[JSON.stringify(shown)]);
 const submit=async()=>{if(pending||!message.trim()||!room)return;setPending(true);setError('');try{if(active)await request(prefix+'chat/steer',{session_id:room.session_id,message:message.trim()});else await request(prefix+'chat',{session_id:room.session_id,message:message.trim(),meeting_id:selected?.id,mode:'chat'});setMessage('');localStorage.removeItem(draftKey);follow.current=true}catch(e){setError(failure(e))}finally{setPending(false)}};
 return <section className="ha-discussion-room" aria-label="회의실">
  <header className="ha-discussion-heading"><div className="min-w-0"><h2><MessageCircle size={20}/>회의</h2><p className="truncate" title={selected?.topic}>{selected?.topic||(preferred?.topic||'새 회의가 시작되면 여기에 표시됩니다.')}</p></div><div className="flex shrink-0 items-center gap-2">{state&&<span className="ha-meeting-badge">{label(state)}</span>}<Button variant="ghost" disabled={!company} onClick={()=>onTalk(company)}><ArrowLeft size={15}/>총괄 대화</Button></div></header>
  <div className="ha-discussion-toolbar">{companies.length>1&&<Select aria-label="회의 조직" value={company} onChange={event=>{setCompany(event.target.value);setMeetingId('')}}>{companies.map(item=><option key={item.id} value={item.id}>{item.title}</option>)}</Select>}{meetings.length>1&&<Select aria-label="회의 안건" value={selected?.id||''} onChange={event=>{setMeetingId(event.target.value);setRole('all');follow.current=true}}>{meetings.map(item=><option key={item.id} value={item.id}>{item.topic} · {label(item.status)}</option>)}</Select>}<nav aria-label="회의 직군"><Button variant="ghost" tone={role==='all'?'primary':'neutral'} onClick={()=>setRole('all')}>전체</Button>{staff.map(person=><Button key={person.role} variant="ghost" tone={role===person.role?'primary':'neutral'} aria-label={person.role+' · '+person.name} title={person.description} onClick={()=>setRole(person.role)}>{person.role} · {person.name}</Button>)}</nav></div>
  {error&&<ErrorMessage message={error}/>}
  <div ref={thread} className="ha-discussion-thread" aria-live="polite" onScroll={()=>{const el=thread.current;if(el)follow.current=el.scrollHeight-el.scrollTop-el.clientHeight<90}}>
   {!companies.length?<div className="ha-discussion-empty"><p>연결된 조직을 찾을 수 없어 회의 기록을 불러올 수 없습니다.</p><p>조직의 설치·연결 상태를 확인하세요. 기존 Hermes 대화는 대화 목록에서 볼 수 있습니다.</p><Button variant="ghost" onClick={()=>{location.hash='projects/manage/installed'}}>설치·연결 확인</Button></div>:!room&&!error&&<p className="ha-discussion-empty">회의에 연결하고 있습니다…</p>}
   {room&&!shown.length&&<p className="ha-discussion-empty">{state==='running'?'안건이 등록됐습니다. 첫 발언을 기다리고 있습니다…':'이 회의의 발언이 아직 없습니다.'}</p>}
   {shown.map((speech,index)=><article key={speech.id||selected?.id+'-'+index+'-'+speech.role} className={'ha-discussion-line '+(speech.role==='OWNER'?'is-owner':speech.source==='failure'?'is-failure':'')}><span className="ha-meeting-avatar">{speech.role==='OWNER'?'대표':speech.role||'직원'}</span><div className="ha-discussion-message"><header><b>{speech.role==='OWNER'?'대표':speech.name||staff.find(person=>person.role===speech.role)?.title||speech.role}</b>{speech.source==='hermes_delegate'&&<small>독립 검토</small>}{speech.status==='speaking'&&<small>답변 중…</small>}{speech.status==='failed'&&<small>발언 중단</small>}</header><div className="ha-discussion-bubble">{speech.statement||speech.content?<MarkdownContent text={displayEngineResponse(speech.statement||speech.content||'')}/>:<span className="ha-typing" aria-label="발언 준비 중">생각을 정리하고 있습니다…</span>}{speech.error&&<p className="mt-2 text-sm text-red-700">{displayEngineResponse(speech.error)}</p>}</div>{speech.source_session_id&&<details className="ha-discussion-source"><summary>발언 정보</summary><p>{speech.role} · Hermes 원본 위임 세션</p><p className="break-all">{speech.source_session_id}</p>{speech.reply_to&&<p>검토 쟁점 · {speech.reply_to}</p>}</details>}</div></article>)}
   {selected?.summary&&!speeches.some(item=>item.source==='moderator'||item.source==='failure')&&<article className="ha-discussion-line"><span className="ha-meeting-avatar">CEO</span><div className="ha-discussion-message"><header><b>총괄 · 저장된 결론</b></header><div className="ha-discussion-bubble"><MarkdownContent text={selected.summary}/></div></div></article>}
   {live?.error&&!speeches.some(item=>item.source==='failure')&&<p className="ha-discussion-empty text-red-700">{displayEngineResponse(live.error)}</p>}
   {selected?.venture_id&&room?.ventures?.some(item=>item.id===selected.venture_id&&item.status==='pending')&&<div className="ha-discussion-proposal"><b>승인 대기 초안이 제출됐습니다.</b><p>총괄 대화의 사업관리에서 검토·수정·승인할 수 있습니다. 아직 실행하지 않습니다.</p><Button onClick={()=>onReview(company)}>사업 초안 검토</Button></div>}
  </div>
  <form className="ha-discussion-composer" onSubmit={event=>{event.preventDefault();void submit()}}><Textarea aria-label="회의에 보낼 메시지" rows={1} placeholder="의견을 남기거나, 더 조사할 내용과 수정 방향을 말하세요…" value={message} onChange={event=>{setMessage(event.target.value);localStorage.setItem(draftKey,event.target.value)}} onKeyDown={event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.nativeEvent.isComposing){event.preventDefault();void submit()}}}/><div><span>Enter 전송 · Shift+Enter 줄바꿈</span>{active&&<Button tone="danger" aria-label="회의 실행 중지" disabled={pending} onClick={()=>void request(prefix+'stop',{}).catch(e=>setError(failure(e)))}><Square size={14}/></Button>}<Button type="submit" tone="primary" aria-label="회의 메시지 보내기" disabled={pending||!message.trim()||!room||active&&status?.job.can_steer===false}><ArrowUp size={18}/></Button></div></form>
 </section>;
}
