import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,Select,ErrorMessage} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import {MarkdownContent} from '@platform/ui/MarkdownContent';
import {failure,prefix,working,type AgentStatus} from '../types';
import {MessagesSquare,ArrowRight,Users} from 'lucide-react';
import {ActivityTimeline} from './ChatStream';
import {displayEngineResponse} from './EngineNotes';

type Speech={role?:string;name?:string;statement?:string;content?:string;reply_to?:string;basis?:string};
type Meeting={id:string;topic:string;status:string;created_at:string;summary?:string;minutes?:Speech[]};
type Staff={role:string;name:string;title:string;description:string;status:string;latest?:{title:string;status:string}};
type Job={id:string;role:string;title:string;status:string;result?:string;summary?:string;error?:string;mode?:string};
type Room={session_id:string;meetings:Meeting[];roles:Staff[];jobs:Job[]};
type Company={id:string;title:string};
const stateLabel=(state:string)=>({running:'진행 중',queued:'대기',completed:'완료',complete:'완료',failed:'실패',paused:'중단',stopped:'중지',idle:'배정 없음'}[state]||state);

export function MeetingRoom({companies,onTalk}:{companies:Company[];onTalk:(id:string)=>void}){
 const [company,setCompany]=useState(companies[0]?.id??''),[room,setRoom]=useState<Room>(),[meetingId,setMeetingId]=useState(''),[role,setRole]=useState('all'),[status,setStatus]=useState<AgentStatus>(),[error,setError]=useState('');
 useEffect(()=>{if(!companies.some(item=>item.id===company))setCompany(companies[0]?.id??'')},[companies,company]);
 useEffect(()=>{if(!company)return;let live=true;let timer:ReturnType<typeof setTimeout>;
  setRoom(undefined);setMeetingId('');setRole('all');setStatus(undefined);setError('');
  const refresh=async()=>{try{const [records,next]=await Promise.all([request<Room>('projects/conversation',{id:company,action:'meetings'}),request<AgentStatus>(prefix+'status',{},'GET')]);if(live){setRoom(records);setStatus(next.job.session_id===records.session_id?next:undefined);setError('')}}catch(e){if(live)setError(failure(e))}finally{if(live)timer=setTimeout(()=>{void refresh()},2500)}};
  void refresh();return()=>{live=false;clearTimeout(timer)};
 },[company]);
 const meetings=room?.meetings??[],selected=meetings.find(item=>item.id===meetingId)??meetings[0],staff=room?.roles??[],speeches=selected?.minutes??[],shown=role==='all'?speeches:speeches.filter(item=>item.role===role),jobs=(room?.jobs??[]).filter(item=>role==='all'||item.role===role),active=working(status);
 const person=staff.find(item=>item.role===role),participants=staff.filter(item=>speeches.some(speech=>speech.role===item.role));
 const date=selected?new Date(selected.created_at).toLocaleString('ko-KR',{month:'long',day:'numeric',hour:'2-digit',minute:'2-digit'}):'';
 return <section className="ha-meeting-room" aria-label="회의실">
  <header className="ha-meeting-heading"><div><p className="ha-meeting-eyebrow">조직 · 협업</p><h2>회의실</h2><p className="ha-meeting-subtitle">직군별 판단과 협업 과정을 살펴보세요.</p></div><div className="flex flex-wrap items-center gap-2">{companies.length>1&&<Select aria-label="회의 조직" value={company} onChange={event=>setCompany(event.target.value)}>{companies.map(item=><option key={item.id} value={item.id}>{item.title}</option>)}</Select>}<Button tone="primary" onClick={()=>onTalk(company)} disabled={!company}><MessagesSquare size={16}/>총괄과 대화<ArrowRight size={15}/></Button></div></header>
  {error&&<ErrorMessage message={error}/>}
  {!room&&!error&&<p className="text-sm text-copy">회의와 직원 정보를 불러오고 있습니다…</p>}
  {room&&<>
   <Panel title="회의 안건" collapsible={false} className="ha-meeting-agenda" actions={<span className="ha-meeting-badge">{selected?stateLabel(selected.status):'기록 없음'}</span>}>
    {selected?<><h3 className="ha-meeting-topic" title={selected.topic}>{selected.topic}</h3><div className="ha-meeting-meta"><span>{date}</span><span><Users size={14}/>{participants.length}개 직군 발언</span><span>저장된 회의</span></div>{meetings.length>1&&<Select className="mt-3 w-full" aria-label="회의 안건" value={selected.id} onChange={event=>{setMeetingId(event.target.value);setRole('all')}}>{meetings.map(item=><option key={item.id} value={item.id}>{item.topic}</option>)}</Select>}</>:<p className="text-sm text-copy">회의가 기록되면 참여 직군과 의견이 여기에 표시됩니다.</p>}
   </Panel>
   {status&&(active||status.job.error)&&<div className="ha-meeting-run" role="status"><b>총괄 실행 · {stateLabel(status.job.state)}</b>{status.job.error&&<p className="mt-1 text-sm text-red-700">{displayEngineResponse(status.job.error)}</p>}<details className="mt-2"><summary className="cursor-pointer text-sm text-brand-700">실행 내역 펼치기</summary><ActivityTimeline job={status.job}/></details></div>}
   <div className="ha-meeting-grid">
    <aside className="ha-meeting-roster"><Panel title="직군" collapsible={false}><nav aria-label="회의 직군" className="ha-meeting-people"><Button variant="ghost" tone={role==='all'?'primary':'neutral'} aria-pressed={role==='all'} className="ha-meeting-person" onClick={()=>setRole('all')}><Users size={18}/><span className="min-w-0 flex-1 text-left">전체 발언</span><span className="text-xs">{speeches.length}</span></Button>{staff.map(item=>{const count=speeches.filter(speech=>speech.role===item.role).length;return <Button key={item.role} variant="ghost" tone={role===item.role?'primary':'neutral'} aria-pressed={role===item.role} aria-label={item.role+' · '+item.name} className="ha-meeting-person" onClick={()=>setRole(item.role)}><span className="ha-meeting-avatar">{item.role}</span><span className="min-w-0 flex-1 text-left"><b className="block truncate">{item.name}</b><small className="block font-normal opacity-70">{count?count+'개 발언':'발언 없음'}</small></span></Button>})}</nav></Panel></aside>
    <main className="ha-meeting-discussion" aria-label="회의 발언"><div className="ha-meeting-section-heading"><h3>{person?person.name+'의 의견':'발언 흐름'}</h3><span>{shown.length}개 발언</span></div><div className="space-y-3">{shown.map((item,index)=>{const text=item.statement||item.content||'',speaker=staff.find(member=>member.role===item.role);return <article key={selected?.id+'-'+index+'-'+item.role} className="ha-meeting-speech"><header><span className="ha-meeting-avatar">{item.role}</span><div className="min-w-0"><b>{item.role} · {item.name||speaker?.title||'의견'}</b><small>발언 {speeches.indexOf(item)+1}</small></div></header>{item.reply_to&&<p className="ha-meeting-reply">응답한 쟁점 · {item.reply_to}</p>}<div className="ha-meeting-excerpt"><MarkdownContent text={text.split(/\n\s*\n/)[0]||'발언 내용이 없습니다.'}/></div><details className="ha-meeting-full"><summary>발언 전문 · 근거 보기</summary><div className="mt-3 text-sm leading-relaxed"><MarkdownContent text={text}/>{item.basis&&<p className="mt-3 text-copy">근거 · {item.basis}</p>}</div></details></article>})}{selected&&!shown.length&&<div className="ha-meeting-empty"><MessagesSquare size={24}/><p>이 직군의 저장된 발언이 없습니다.</p></div>}</div>
     {selected?.summary&&<Panel title="회의 결론" collapsible defaultCollapsed description="총괄의 보고 내용과 합의·쟁점을 확인합니다."><div className="text-sm leading-relaxed"><MarkdownContent text={selected.summary}/></div></Panel>}
    </main>
    <aside className="ha-meeting-inspector">{person?<Panel title={person.role+' · 담당 역할'} collapsible={false}><h3 className="font-semibold text-ink">{person.title}</h3><p className="mt-2 text-sm leading-relaxed text-copy">{person.description}</p>{person.latest&&<div className="ha-meeting-latest"><span>최근 담당 업무 · {stateLabel(person.latest.status)}</span><p>{person.latest.title}</p></div>}<Panel title="업무 기록" collapsible defaultCollapsed className="ha-meeting-job-panel"><div className="divide-y divide-slate-100">{jobs.map(item=><details key={item.id} className="py-3"><summary className="cursor-pointer text-sm"><span className="text-copy">{stateLabel(item.status)}</span><span className="mt-1 block">{item.title}</span></summary><div className="mt-2 text-sm"><MarkdownContent text={displayEngineResponse(item.error||item.result||item.summary||'최종 결과가 아직 기록되지 않았습니다.')}/></div></details>)}{!jobs.length&&<p className="text-sm text-copy">배정 기록이 없습니다.</p>}</div></Panel></Panel>:<Panel title="배치 살펴보기" collapsible={false}><p className="text-sm leading-relaxed text-copy">직군을 선택하면 발언과 담당 업무를 함께 볼 수 있습니다.</p><p className="mt-3 text-sm leading-relaxed text-copy">역할이 겹치거나 빠진 곳, 근거가 부족한 의견을 살펴보고 총괄에게 조정을 요청하세요.</p></Panel>}</aside>
   </div>
  </>}
 </section>;
}
