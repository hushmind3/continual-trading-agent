import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,Select,ErrorMessage} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import {MarkdownContent} from '@platform/ui/MarkdownContent';
import {failure,prefix,working,type AgentStatus} from '../types';
import {ActivityTimeline} from './ChatStream';
import {displayEngineResponse} from './EngineNotes';

type Speech={role?:string;name?:string;statement?:string;content?:string;reply_to?:string;basis?:string};
type Meeting={id:string;topic:string;status:string;created_at:string;summary?:string;minutes?:Speech[]};
type Staff={role:string;name:string;title:string;description:string;status:string;latest?:{title:string;status:string}};
type Job={id:string;role:string;title:string;status:string;result?:string;summary?:string;error?:string;mode?:string};
type Room={session_id:string;meetings:Meeting[];roles:Staff[];jobs:Job[]};
type Company={id:string;title:string};
const stateLabel=(state:string)=>({running:'진행 중',queued:'대기',completed:'완료',complete:'완료',failed:'실패',paused:'중단',stopped:'중지',idle:'배정 없음'}[state]||state);

export function MeetingRoom({companies}:{companies:Company[]}){
 const [company,setCompany]=useState(companies[0]?.id??''),[room,setRoom]=useState<Room>(),[meetingId,setMeetingId]=useState(''),[role,setRole]=useState('all'),[status,setStatus]=useState<AgentStatus>(),[error,setError]=useState('');
 useEffect(()=>{if(!companies.some(item=>item.id===company))setCompany(companies[0]?.id??'')},[companies,company]);
 useEffect(()=>{if(!company)return;let live=true;let timer:ReturnType<typeof setTimeout>;
  setRoom(undefined);setMeetingId('');setRole('all');setStatus(undefined);setError('');
  const refresh=async()=>{try{const [records,next]=await Promise.all([request<Room>('projects/conversation',{id:company,action:'meetings'}),request<AgentStatus>(prefix+'status',{},'GET')]);if(live){setRoom(records);setStatus(next.job.session_id===records.session_id?next:undefined);setError('')}}catch(e){if(live)setError(failure(e))}finally{if(live)timer=setTimeout(()=>{void refresh()},2500)}};
  void refresh();return()=>{live=false;clearTimeout(timer)};
 },[company]);
 const meetings=room?.meetings??[],selected=meetings.find(item=>item.id===meetingId)??meetings[0],staff=room?.roles??[],speeches=selected?.minutes??[],shown=role==='all'?speeches:speeches.filter(item=>item.role===role),jobs=(room?.jobs??[]).filter(item=>role==='all'||item.role===role),active=working(status);
 return <section className="flex min-h-0 flex-1 flex-col overflow-y-auto bg-slate-50 p-4 text-ink md:p-6" aria-label="회의실">
  <header className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-semibold">회의</h2><p className="mt-1 text-sm text-copy">직군별 의견과 결론, 실제 업무 배정을 확인합니다.</p></div>{companies.length>1&&<Select aria-label="회의 조직" value={company} onChange={event=>setCompany(event.target.value)}>{companies.map(item=><option key={item.id} value={item.id}>{item.title}</option>)}</Select>}</header>
  {error&&<ErrorMessage message={error}/>}
  {!room&&!error&&<p className="text-sm text-copy">저장된 회의와 직원 정보를 불러오고 있습니다…</p>}
  {room&&<div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(16rem,22rem)]"><div className="min-w-0 space-y-4">
   {status&&<Panel title={'현재 총괄 실행 · '+stateLabel(status.job.state)} collapsible={false}>{status.job.error?<p role="status" className="mt-2 text-sm text-red-700">{displayEngineResponse(status.job.error)}</p>:<p className="mt-2 text-sm text-copy">{active?'총괄이 작업 중입니다. 아래 저장 발언과 실제 도구 실행이 갱신됩니다.':'실행 중인 총괄 작업은 없습니다.'}</p>}<details className="mt-3"><summary className="cursor-pointer text-sm text-brand">실제 실행 과정 보기</summary><ActivityTimeline job={status.job}/></details></Panel>}
   <Panel title="회의 안건" collapsible={false}>{meetings.length?<><Select className="mt-3 w-full" aria-label="회의 안건" value={selected?.id??''} onChange={event=>{setMeetingId(event.target.value);setRole('all')}}>{meetings.map(item=><option key={item.id} value={item.id}>{item.topic}</option>)}</Select><p className="mt-3 text-sm text-copy">{stateLabel(selected.status)} · {selected.created_at}</p><p className="mt-2 text-sm text-copy">저장된 회의 발언입니다. 직군 이름만으로 독립 에이전트 실행을 뜻하지 않습니다.</p></>:<p className="mt-3 text-sm text-copy">저장된 회의가 없습니다. 발언이 기록되면 여기에 표시됩니다.</p>}</Panel>
   <nav className="flex flex-wrap gap-2" aria-label="회의 직군"><Button variant="ghost" tone={role==='all'?'primary':'neutral'} onClick={()=>setRole('all')}>전체 발언</Button>{staff.map(item=><Button key={item.role} variant="ghost" tone={role===item.role?'primary':'neutral'} onClick={()=>setRole(item.role)}>{item.role} · {item.name}</Button>)}</nav>
   <div className="space-y-3" aria-live="polite">{shown.map((item,index)=><details key={selected?.id+'-'+index+'-'+item.role} className="rounded-2xl border border-slate-200 bg-white p-4" open={role!=='all'}><summary className="cursor-pointer font-semibold">{speeches.indexOf(item)+1}. {item.role} · {item.name||staff.find(person=>person.role===item.role)?.title||'의견'}</summary><div className="mt-3 text-sm leading-relaxed">{item.reply_to&&<p className="mb-2 text-copy">응답한 쟁점 · {item.reply_to}</p>}<MarkdownContent text={item.statement||item.content||'발언 내용이 없습니다.'}/>{item.basis&&<p className="mt-2 text-copy">근거 · {item.basis}</p>}</div></details>)}{selected&&!shown.length&&<p className="text-sm text-copy">이 직군의 저장된 발언이 없습니다.</p>}</div>
   {selected?.summary&&<details className="rounded-2xl border border-slate-200 bg-white p-4"><summary className="cursor-pointer font-semibold">총괄 결론 · 합의와 남은 쟁점</summary><div className="mt-3 text-sm leading-relaxed"><MarkdownContent text={selected.summary}/></div></details>}
  </div><aside className="min-w-0 space-y-4"><Panel title="직군 · 담당 관점" collapsible={false}><p className="mt-2 text-sm text-copy">현재 조직의 역할 정의입니다. 전문성은 실제 결과로 판단합니다.</p><div className="mt-3 divide-y divide-slate-100">{staff.filter(item=>role==='all'||item.role===role).map(item=><div key={item.role} className="py-3"><b className="text-sm">{item.role} · {item.title}</b><p className="mt-1 text-sm text-copy">{item.description}</p>{item.latest&&<p className="mt-2 text-xs text-copy">최근 업무 · {stateLabel(item.latest.status)} · {item.latest.title}</p>}</div>)}</div></Panel><Panel title="업무 배정 기록" collapsible={false}><p className="mt-2 text-xs text-copy">현재 선택한 회의와 같은 조직의 업무입니다. 해당 회의에서 배정됐다는 뜻은 아닙니다.</p><div className="mt-3 divide-y divide-slate-100">{jobs.map(item=><details key={item.id} className="py-3"><summary className="cursor-pointer text-sm">{item.role} · {stateLabel(item.status)}<span className="mt-1 block text-copy">{item.title}</span></summary><div className="mt-2 text-sm"><MarkdownContent text={displayEngineResponse(item.error||item.result||item.summary||'최종 결과가 아직 기록되지 않았습니다.')}/></div></details>)}{!jobs.length&&<p className="text-sm text-copy">해당 직군의 배정 기록이 없습니다.</p>}</div></Panel></aside></div>}
 </section>;
}
