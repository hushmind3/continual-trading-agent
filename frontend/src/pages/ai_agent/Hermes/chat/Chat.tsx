import {useEffect,useRef,useState} from 'react';
import {ArrowDown} from 'lucide-react';
import {request} from '../../../../data/api';
import {Button,IconButton,Textarea,ErrorMessage} from '../../../../ui/Primitives';
import {prefix,failure,working,contentText,type AgentStatus,type Message,type Session,type SessionDetail,type AutonomousState} from '../types';
import {Transcript,CurrentActivity} from './ChatStream';
import {MessageBody} from './MessageBody';
import {ChatHeader} from './ChatHeader';
import {SessionSidebar} from './SessionSidebar';
import {ActivityPanel} from './ActivityPanel';
import {ChatComposer} from './ChatComposer';
import {ChatWelcome} from './ChatWelcome';

interface Props {status?:AgentStatus;modelName:string;focused:boolean;onFocus:()=>void;onStatus:(s:AgentStatus)=>void;onModels:()=>void;onSettings:()=>void;onRefresh:()=>void}
const draftKey=(id:string)=>'hermes.draft.'+(id||'new');
const mobile=()=>window.matchMedia('(max-width:760px)').matches;
export function Chat({status,modelName,focused,onFocus,onStatus,onModels,onSettings,onRefresh}:Props){
 const [sessions,setSessions]=useState<Session[]>([]),[selected,setSelected]=useState(''),[messages,setMessages]=useState<Message[]>([]),[text,setText]=useState(()=>localStorage.getItem(draftKey(''))||''),[error,setError]=useState(''),[pending,setPending]=useState(false),[optimistic,setOptimistic]=useState('');
 const [sessionsOpen,setSessionsOpen]=useState(()=>!mobile()&&localStorage.getItem('hermes.sessions.open')==='true'),[activityOpen,setActivityOpen]=useState(false),[query,setQuery]=useState(''),[showLatest,setShowLatest]=useState(false);
 const viewport=useRef<HTMLDivElement>(null),follow=useRef(true),selection=useRef(''),composer=useRef<HTMLTextAreaElement>(null);
 const sessionPanel=useRef<HTMLElement>(null),activityPanel=useRef<HTMLElement>(null),sessionButton=useRef<HTMLButtonElement>(null),activityButton=useRef<HTMLButtonElement>(null);
 const [answer,setAnswer]=useState(''),[mode,setMode]=useState('chat'),[turns,setTurns]=useState(20),[interval,setIntervalSeconds]=useState(60),[times,setTimes]=useState(5),[savedAutonomy,setSavedAutonomy]=useState<AutonomousState>();
 const active=working(status),thisJob=status?.job.session_id===selected?status.job:undefined,auto=thisJob?.autonomy??savedAutonomy;
 const toggleSessions=()=>setSessionsOpen(v=>{localStorage.setItem('hermes.sessions.open',String(!v));if(!v&&mobile())setActivityOpen(false);return !v});
 const draft=(value:string)=>{setText(value);try{localStorage.setItem(draftKey(selected),value)}catch{/* Keep typing if local storage is full. */}};
 const list=async()=>{const rows=await request<Session[]>(prefix+'sessions',{},'GET');setSessions(rows);return rows};
 const choose=async(id:string)=>{
  follow.current=true;setShowLatest(false);sessionStorage.setItem('hermes.session',id);selection.current=id;setSelected(id);setText(localStorage.getItem(draftKey(id))||'');setOptimistic('');setMessages([]);setSavedAutonomy(undefined);setError('');if(mobile())setSessionsOpen(false);
  try{const data=await request<SessionDetail>(prefix+'session',{id},'GET');if(selection.current===id){setMessages(data.messages);const a=await request<{goal?:Record<string,unknown>;loop?:Record<string,unknown>}>(prefix+'autonomy',{id},'GET');if(selection.current===id){const [kind,state]=a.loop?.status==='active'?['loop',a.loop]:a.goal?.status==='active'?['goal',a.goal]:a.loop?.status==='paused'?['loop',a.loop]:['goal',a.goal];setSavedAutonomy(state?{...state,mode:kind} as AutonomousState:undefined)}}}catch(e){if(selection.current===id)setError(failure(e))}
 };
 useEffect(()=>{let disposed=false;void list().then(rows=>{if(!disposed&&rows.length)void choose(rows.find(r=>r.id===sessionStorage.getItem('hermes.session'))?.id??rows[0].id)}).catch(e=>{if(!disposed)setError(failure(e))});return()=>{disposed=true}},[]);
 useEffect(()=>{if(!status?.job.session_id)return;if(['complete','failed','stopped','paused'].includes(status.job.state)){void list().catch(e=>setError(failure(e)));if(selection.current===status.job.session_id)void request<SessionDetail>(prefix+'session',{id:selection.current},'GET').then(row=>{if(selection.current===row.session.id){setMessages(row.messages);setOptimistic('')}}).catch(e=>setError(failure(e)))}},[status?.job.state,status?.job.session_id]);
 useEffect(()=>{if(follow.current&&viewport.current)viewport.current.scrollTop=viewport.current.scrollHeight},[messages,status?.job.live_text]);
 useEffect(()=>{if(!active||!selected||status?.job.session_id!==selected)return;let live=true;const poll=()=>{void request<SessionDetail>(prefix+'session',{id:selected},'GET').then(row=>{if(live&&selection.current===row.session.id)setMessages(prev=>JSON.stringify(prev)===JSON.stringify(row.messages)?prev:row.messages)}).catch(()=>{})};poll();const timer=setInterval(poll,2500);return()=>{live=false;clearInterval(timer)}},[active,selected,status?.job.session_id]);
 useEffect(()=>{
  const panel=activityOpen?activityPanel.current:sessionsOpen?sessionPanel.current:null,origin=document.activeElement as HTMLElement|null;
  if(panel&&mobile())panel.querySelector<HTMLElement>('button,input')?.focus();
  const keys=(e:KeyboardEvent)=>{
   if(e.key==='Escape'){if(activityOpen){setActivityOpen(false);activityButton.current?.focus()}else if(sessionsOpen){setSessionsOpen(false);sessionButton.current?.focus()}}
   if(e.key==='Tab'&&panel&&mobile()){const focusable=[...panel.querySelectorAll<HTMLElement>('button:not(:disabled),input,select,textarea,summary,a[href]')];const first=focusable[0],last=focusable.at(-1);if(!first||!last)return;if(e.shiftKey&&(document.activeElement===first||!panel.contains(document.activeElement))){e.preventDefault();last.focus()}else if(!e.shiftKey&&(document.activeElement===last||!panel.contains(document.activeElement))){e.preventDefault();first.focus()}}
  };
  window.addEventListener('keydown',keys);return()=>{window.removeEventListener('keydown',keys);if(panel&&mobile())origin?.focus()};
 },[sessionsOpen,activityOpen]);
 const create=async()=>{setPending(true);setError('');try{const row=await request<SessionDetail>(prefix+'session/create',{});await list();await choose(row.session.id);composer.current?.focus()}catch(e){setError(failure(e))}finally{setPending(false)}};
 const send=async()=>{if(!text.trim()||pending||active)return;const prompt=text.trim();setPending(true);setError('');follow.current=true;setShowLatest(false);try{const next=await request<AgentStatus>(prefix+'chat',{session_id:selected||undefined,message:prompt,mode,max_turns:turns,times,interval_seconds:interval||null});localStorage.removeItem(draftKey(selected));selection.current=next.job.session_id??'';setSelected(selection.current);setOptimistic(prompt);setText('');onStatus(next);await list()}catch(e){setError(failure(e))}finally{setPending(false)}};
 const stop=async()=>{setPending(true);try{onStatus(await request<AgentStatus>(prefix+'stop',{}))}catch(e){setError(failure(e))}finally{setPending(false)}};
 const archive=async()=>{if(!selected)return;setPending(true);try{await request(prefix+'session/archive',{id:selected});selection.current='';setSelected('');setMessages([]);setText(localStorage.getItem(draftKey(''))||'');setSavedAutonomy(undefined);setOptimistic('');await list()}catch(e){setError(failure(e))}finally{setPending(false)}};
 const resume=async()=>{if(!auto)return;setPending(true);setError('');try{onStatus(await request<AgentStatus>(prefix+'chat',{session_id:selected,message:auto.goal??auto.prompt,mode:auto.mode,resume:true}))}catch(e){setError(failure(e))}finally{setPending(false)}};
 const respond=async(allow:boolean)=>{setPending(true);setError('');try{await request(prefix+'answer',{allow,text:answer});setAnswer('')}catch(e){setError(failure(e))}finally{setPending(false)}};
 const title=sessions.find(r=>r.id===selected)?.title||'새 대화',shownModel=modelName||sessions.find(r=>r.id===selected)?.model;
 const visible=sessions.filter(r=>(r.title||'제목 없는 대화').toLowerCase().includes(query.toLowerCase()));
 const empty=!messages.length&&!optimistic&&!(thisJob?.live_text&&active);
 return <div className={'hermes-chat-layout '+(sessionsOpen?'sessions-open':'sessions-closed')}>
 {sessionsOpen&&<><IconButton className="ha-panel-backdrop" aria-label="대화 목록 배경 닫기" tabIndex={-1} onClick={()=>setSessionsOpen(false)}/><SessionSidebar sessionPanel={sessionPanel} toggleSessions={toggleSessions} create={()=>void create()} pending={pending} query={query} setQuery={setQuery} visible={visible} selected={selected} choose={id=>void choose(id)} onSettings={onSettings}/></>}
 <section className="hermes-chat"><ChatHeader sessionsOpen={sessionsOpen} sessionButton={sessionButton} title={title} shownModel={shownModel} modelReady={status?.local_model.state==='ready'} metrics={thisJob?.metrics??{context_limit:status?.job.metrics?.context_limit}} pending={pending} create={()=>void create()} activityButton={activityButton} activityOpen={activityOpen} toggleActivity={()=>{setActivityOpen(v=>!v);if(mobile())setSessionsOpen(false)}} focused={focused} onFocus={onFocus} onModels={onModels} onSettings={onSettings} toggleSessions={toggleSessions}/>

 <div className="hermes-chat-body"><div ref={viewport} className={'hermes-messages '+(empty?'is-empty':'')} onScroll={()=>{const el=viewport.current;if(el){follow.current=el.scrollHeight-el.scrollTop-el.clientHeight<90;setShowLatest(!follow.current)}}}><div className="ha-conversation" aria-live="polite">
 {empty&&<ChatWelcome onPick={value=>{draft(value);composer.current?.focus()}}/>}
 <Transcript messages={messages}/>
 {optimistic&&!messages.some(m=>m.role==='user'&&contentText(m.content)===optimistic)&&<article className="hermes-message user"><div className="ha-message-content"><MessageBody text={optimistic} user/></div></article>}
 {thisJob?.live_text&&active&&contentText(messages.at(-1)?.content)!==thisJob.live_text&&<article className="hermes-message assistant is-streaming"><div className="ha-assistant-mark">✳</div><div className="ha-message-content"><MessageBody text={thisJob.live_text}/><span className="ha-stream-dot" aria-label="답변 작성 중"/></div></article>}
 </div></div>{showLatest&&<IconButton className="ha-scroll-latest" type="button" aria-label="최신 메시지로 이동" onClick={()=>{follow.current=true;setShowLatest(false);viewport.current?.scrollTo({top:viewport.current.scrollHeight,behavior:'smooth'})}}><ArrowDown size={17}/>최신 메시지</IconButton>}
 {activityOpen&&<><IconButton className="ha-panel-backdrop ha-activity-backdrop" aria-label="작업 내역 배경 닫기" tabIndex={-1} onClick={()=>setActivityOpen(false)}/><ActivityPanel activityPanel={activityPanel} thisJob={thisJob} selected={selected} pending={pending} active={active} onClose={()=>setActivityOpen(false)} onRefresh={onRefresh} archive={()=>void archive()}/></>}</div>
 <div className="ha-composer-dock">
 {thisJob?.approval&&<div className="hermes-approval"><b>{thisJob.approval.kind==='question'?'헤르메스의 질문':'작업 실행 확인'}</b><details><summary>요청 내용 보기</summary><pre>{thisJob.approval.detail}</pre></details>{thisJob.approval.kind==='question'?<><Textarea aria-label="헤르메스 질문에 답변" value={answer} onChange={e=>setAnswer(e.target.value)}/><Button disabled={pending||!answer.trim()} onClick={()=>void respond(true)}>답변 보내기</Button></>:<div className="hermes-actions"><Button tone="primary" disabled={pending} onClick={()=>void respond(true)}>허용</Button><Button disabled={pending} onClick={()=>void respond(false)}>거절</Button></div>}</div>}
 {active&&!thisJob?<div className="hermes-current-activity is-active"><span>다른 대화에서 작업 중입니다.</span><Button onClick={()=>void choose(status?.job.session_id??'')}>해당 대화로 이동</Button></div>:<CurrentActivity job={thisJob} active={active&&!!thisJob}/>}
 {auto&&['active','paused'].includes(auto.status)&&<div className="hermes-autonomy-state"><b>{auto.mode==='goal'?'목표 실행':'반복 실행'}</b><span>{auto.status==='paused'?'일시정지':'진행 중'} · {auto.mode==='goal'?String(auto.turns_used??0)+'/'+String(auto.max_turns??0)+'회':String(auto.ticks_fired??0)+'회 실행'}</span>{auto.status==='paused'&&!active&&<Button disabled={pending} onClick={()=>void resume()}>재개</Button>}<details><summary>판정 내용</summary><p>{auto.paused_reason||auto.last_stop_reason||auto.last_reason||'진행 중입니다.'}</p></details></div>}
 <ErrorMessage message={error||thisJob?.error||''}/>
 <ChatComposer composer={composer} text={text} draft={draft} send={()=>void send()} stop={()=>void stop()} active={active} pending={pending} stopping={status?.job.state==='stopping'} mode={mode} setMode={setMode} turns={turns} setTurns={setTurns} interval={interval} setIntervalSeconds={setIntervalSeconds} times={times} setTimes={setTimes}/></div>
 </section></div>;
}
