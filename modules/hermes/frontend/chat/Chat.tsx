import {DocumentWorkspace,DocumentPanel,useDocumentWorkspace} from '@platform/ui/DocumentPreview';
import {useEffect,useRef,useState} from 'react';
import {ArrowDown} from 'lucide-react';
import {request} from '@platform/data/api';
import {Button,IconButton,Textarea,ErrorMessage} from '@platform/ui/Primitives';
import {prefix,failure,working,contentText,type AgentStatus,type Message,type Session,type SessionDetail,type AutonomousState} from '../types';
import {Transcript} from './ChatStream';
import {MessageBody} from './MessageBody';
import {ChatHeader} from './ChatHeader';
import {SessionSidebar} from './SessionSidebar';
import {ActivityPanel} from './ActivityPanel';
import {ChatComposer,type Attachment} from './ChatComposer';
import {ChatWelcome} from './ChatWelcome';
import {useThinking} from './useThinking';
import {AppTabs} from './AppTabs';
import {CompanyPanel} from './CompanyPanel';
import {companySession,useCompanyConversation} from './CompanyConversation';

interface Props {status?:AgentStatus;modelName:string;focused:boolean;onFocus:()=>void;onStatus:(s:AgentStatus)=>void;onModels:()=>void;onSettings:()=>void;onRefresh:()=>void}
const draftKey=(id:string)=>'hermes.draft.'+(id||'new');
const mobile=()=>window.matchMedia('(max-width:760px)').matches;
export function Chat(props:Props){return <AppTabs onModels={props.onModels} modelName={props.modelName} modelState={props.status?.local_model.state}><DocumentWorkspace><ChatWorkspace {...props}/></DocumentWorkspace></AppTabs>;}
function ChatWorkspace({status,modelName,focused,onFocus,onStatus,onModels,onSettings,onRefresh}:Props){
 const documents=useDocumentWorkspace();
 const thinking=useThinking(modelName);
 const [readOnly,updateReadOnly]=useState(()=>localStorage.getItem('hermes.read-mode')==='true');
 const setReadOnly=(value:boolean)=>{updateReadOnly(value);try{localStorage.setItem('hermes.read-mode',String(value))}catch{/* The switch also works without storage. */}};
 const [attachments,setAttachments]=useState<Attachment[]>([]),[uploading,setUploading]=useState(false);
 const upload=async(files:File[])=>{if(uploading)return;if(files.length+attachments.length>8){setError('첨부 파일은 최대 8개입니다.');return}setUploading(true);setError('');try{for(const file of files){if(file.size>8*1024*1024)throw new Error(file.name+': 파일당 최대 8 MiB입니다.');const content=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]??'');reader.onerror=()=>reject(new Error('파일을 읽지 못했습니다.'));reader.readAsDataURL(file)});const saved=await request<Attachment>(prefix+'artifact/upload',{name:file.name,content});setAttachments(previous=>[...previous,saved])}}catch(error){setError(failure(error))}finally{setUploading(false)}};
 const [sessions,setSessions]=useState<Session[]>([]),[selected,setSelected]=useState(''),[messages,setMessages]=useState<Message[]>([]),[text,setText]=useState(()=>localStorage.getItem(draftKey(''))||''),[error,setError]=useState(''),[pending,setPending]=useState(false),[optimistic,setOptimistic]=useState('');
 const [sessionsOpen,setSessionsOpen]=useState(false),[activityOpen,setActivityOpen]=useState(false),[query,setQuery]=useState(''),[showLatest,setShowLatest]=useState(false);
 const [companyOpen,setCompanyOpen]=useState(()=>!mobile());
 const companyPanel=useRef<HTMLElement>(null);
 const viewport=useRef<HTMLDivElement>(null),follow=useRef(true),selection=useRef(''),optimisticAfter=useRef(0),composer=useRef<HTMLTextAreaElement>(null);
 const sessionPanel=useRef<HTMLElement>(null),activityPanel=useRef<HTMLElement>(null),sessionButton=useRef<HTMLButtonElement>(null),activityButton=useRef<HTMLButtonElement>(null);
 const [answer,setAnswer]=useState(''),[mode,setMode]=useState('chat'),[turns,setTurns]=useState(20),[interval,setIntervalSeconds]=useState(60),[times,setTimes]=useState(5),[savedAutonomy,setSavedAutonomy]=useState<AutonomousState>();
 const company=useCompanyConversation(selected);
 const pendingDrafts=company.ventures.map(v=>v.id).join(',');
 useEffect(()=>{if(company.enabled&&pendingDrafts){setCompanyOpen(true);setActivityOpen(false);setSessionsOpen(false)}},[company.enabled,pendingDrafts]);
 const active=working(status),thisJob=status?.job.session_id===selected?status.job:undefined,auto=thisJob?.autonomy??savedAutonomy;
 const shownMessages=messages;
 const toggleCompany=()=>{setCompanyOpen(value=>{localStorage.setItem('hermes.company.open',String(!value));return !value});setActivityOpen(false);setSessionsOpen(false);documents?.close()};
 useEffect(()=>{const media=window.matchMedia('(max-width:760px)');const change=()=>{if(media.matches)setCompanyOpen(false)};media.addEventListener('change',change);return()=>media.removeEventListener('change',change)},[]);
 const toggleSessions=()=>setSessionsOpen(value=>{if(!value){setActivityOpen(false);setCompanyOpen(false);documents?.close()}return !value});
 const draft=(value:string)=>{setText(value);try{localStorage.setItem(draftKey(selected),value)}catch{/* Keep typing if local storage is full. */}};
 const list=async()=>{const rows=await request<Session[]>(prefix+'sessions',{},'GET');const all=[...rows.filter(r=>!company.sources.some(v=>v.session_id===r.id)),...company.sources.map(v=>({id:v.session_id,title:v.title,managed:true}))];setSessions(all);return all};
 const choose=async(id:string)=>{
  const linked=company.sources.find(v=>v.session_id===id||companySession(v.id)===id);
  if(linked){try{id=(await request<{session_id:string}>('projects/conversation',{id:linked.id,action:'session'})).session_id}catch(e){setError(failure(e));return}}
  setAttachments([]);follow.current=true;setShowLatest(false);sessionStorage.setItem('hermes.session',id);selection.current=id;setSelected(id);setText(localStorage.getItem(draftKey(id))||'');setOptimistic('');setMessages([]);setSavedAutonomy(undefined);setError('');setSessionsOpen(false);
  if(!id)return;
  try{const data=await request<SessionDetail>(prefix+'session',{id},'GET');if(selection.current===id){setMessages(data.messages);const a=await request<{goal?:Record<string,unknown>;loop?:Record<string,unknown>}>(prefix+'autonomy',{id},'GET');if(selection.current===id){const [kind,state]=a.loop?.status==='active'?['loop',a.loop]:a.goal?.status==='active'?['goal',a.goal]:a.loop?.status==='paused'?['loop',a.loop]:['goal',a.goal];setSavedAutonomy(state?{...state,mode:kind} as AutonomousState:undefined)}}}catch(e){if(selection.current===id)setError(failure(e))}
 };
 useEffect(()=>{if(documents?.current){setSessionsOpen(false);setActivityOpen(false);setCompanyOpen(false)}},[documents?.current]);
 useEffect(()=>{let disposed=false;void list().then(rows=>{if(!disposed&&rows.length){void choose(rows.find(r=>r.id===sessionStorage.getItem('hermes.session'))?.id??rows[0].id)}}).catch(e=>{if(!disposed)setError(failure(e))});return()=>{disposed=true}},[company.sources.map(v=>v.id).join(',')]);
 useEffect(()=>{const receive=(event:Event)=>{void choose(companySession((event as CustomEvent<string>).detail))};window.addEventListener('hermes:company-conversation',receive);return()=>window.removeEventListener('hermes:company-conversation',receive)},[company.sources.map(v=>v.id).join(',')]);
 useEffect(()=>{if(!status?.job.session_id)return;if(['complete','failed','stopped','paused'].includes(status.job.state)){void list().catch(e=>setError(failure(e)));if(selection.current===status.job.session_id)void request<SessionDetail>(prefix+'session',{id:selection.current},'GET').then(row=>{if(selection.current===row.session.id){setMessages(row.messages);setOptimistic('')}}).catch(e=>setError(failure(e)))}},[status?.job.state,status?.job.session_id]);
 useEffect(()=>{if(follow.current&&viewport.current)viewport.current.scrollTop=viewport.current.scrollHeight},[messages,status?.job.live_text]);
 useEffect(()=>{if(!active||!selected||status?.job.session_id!==selected)return;let live=true;const poll=()=>{void request<SessionDetail>(prefix+'session',{id:selected},'GET').then(row=>{if(live&&selection.current===row.session.id)setMessages(prev=>JSON.stringify(prev)===JSON.stringify(row.messages)?prev:row.messages)}).catch(()=>{})};poll();const timer=setInterval(poll,2500);return()=>{live=false;clearInterval(timer)}},[active,selected,status?.job.session_id]);
 useEffect(()=>{
  const panel=activityOpen?activityPanel.current:sessionsOpen?sessionPanel.current:companyOpen?companyPanel.current:null,origin=document.activeElement as HTMLElement|null;
  if(panel&&(mobile()||sessionsOpen))panel.querySelector<HTMLElement>('button,input')?.focus();
  const keys=(e:KeyboardEvent)=>{
   if(e.key==='Escape'){if(activityOpen){setActivityOpen(false);activityButton.current?.focus()}else if(sessionsOpen){setSessionsOpen(false);sessionButton.current?.focus()}else if(companyOpen){setCompanyOpen(false);document.querySelector<HTMLButtonElement>('[aria-label="사업 관리 보기"]')?.focus()}}
   if(e.key==='Tab'&&panel&&(mobile()||sessionsOpen)){const focusable=[...panel.querySelectorAll<HTMLElement>('button:not(:disabled),input,select,textarea,summary,a[href]')];const first=focusable[0],last=focusable.at(-1);if(!first||!last)return;if(e.shiftKey&&(document.activeElement===first||!panel.contains(document.activeElement))){e.preventDefault();last.focus()}else if(!e.shiftKey&&(document.activeElement===last||!panel.contains(document.activeElement))){e.preventDefault();first.focus()}}
  };
  window.addEventListener('keydown',keys);return()=>{window.removeEventListener('keydown',keys);if(panel&&(mobile()||sessionsOpen))origin?.focus()};
 },[sessionsOpen,activityOpen,companyOpen]);
 const create=async()=>{setPending(true);setError('');try{const row=await request<SessionDetail>(prefix+'session/create',{});await list();await choose(row.session.id);composer.current?.focus()}catch(e){setError(failure(e))}finally{setPending(false)}};
 const send=async()=>{if((!text.trim()&&!attachments.length)||pending||company.pending||active||uploading)return;const prompt=(text.trim()||'첨부 파일을 확인해 주세요.')+(attachments.length?'\n\n첨부 파일:\n'+attachments.map(file=>'['+file.name+']('+file.path.replaceAll('\\','/')+')').join('\n'):'');setPending(true);setError('');follow.current=true;setShowLatest(false);try{await thinking.prepare();const next=await request<AgentStatus>(prefix+'chat',{session_id:selected||undefined,message:prompt,attachments:attachments.map(file=>file.path),read_only:readOnly,mode,max_turns:turns,times,interval_seconds:interval||null});localStorage.removeItem(draftKey(selected));optimisticAfter.current=next.job.session_id===selected?messages.length:0;if(next.job.session_id!==selected)setMessages([]);selection.current=next.job.session_id??'';sessionStorage.setItem('hermes.session',selection.current);setSelected(selection.current);setOptimistic(prompt);setText('');setAttachments([]);onStatus(next);await list()}catch(e){setError(failure(e))}finally{setPending(false)}};
 const stop=async()=>{setPending(true);try{onStatus(await request<AgentStatus>(prefix+'stop',{}))}catch(e){setError(failure(e))}finally{setPending(false)}};
 const archive=async()=>{if(!selected)return;setPending(true);try{await request(prefix+'session/archive',{id:selected});selection.current='';sessionStorage.removeItem('hermes.session');setSelected('');setMessages([]);setText(localStorage.getItem(draftKey(''))||'');setSavedAutonomy(undefined);setOptimistic('');await list()}catch(e){setError(failure(e))}finally{setPending(false)}};
 const resume=async()=>{if(!auto)return;setPending(true);setError('');try{await thinking.prepare();onStatus(await request<AgentStatus>(prefix+'chat',{session_id:selected,message:auto.goal??auto.prompt,mode:auto.mode,resume:true,read_only:readOnly}))}catch(e){setError(failure(e))}finally{setPending(false)}};
 const respond=async(allow:boolean)=>{setPending(true);setError('');try{await request(prefix+'answer',{allow,text:answer});setAnswer('')}catch(e){setError(failure(e))}finally{setPending(false)}};
 const title=sessions.find(r=>r.id===selected)?.title||'새 대화',shownModel=modelName||sessions.find(r=>r.id===selected)?.model;
 const visible=sessions.filter(r=>(r.title||'제목 없는 대화').toLowerCase().includes(query.toLowerCase()));
 const empty=!shownMessages.length&&!optimistic&&!(thisJob?.live_text&&active);
 return <div className={'hermes-chat-layout '+(sessionsOpen?'sessions-open':'sessions-closed')}>
 {sessionsOpen&&<><IconButton className="ha-panel-backdrop ha-session-backdrop" aria-label="대화 목록 배경 닫기" tabIndex={-1} onClick={()=>setSessionsOpen(false)}/><SessionSidebar sessionPanel={sessionPanel} toggleSessions={toggleSessions} create={()=>void create()} pending={pending} query={query} setQuery={setQuery} visible={visible} selected={selected} choose={id=>void choose(id)} archive={()=>void archive()} archiveDisabled={company.enabled||active&&!!thisJob} rename={async(id,title)=>{await request(prefix+'session/rename',{id,title});await list()}}/></>}
 <section className="hermes-chat"><ChatHeader sessionsOpen={sessionsOpen} sessionButton={sessionButton} title={title} shownModel={shownModel} modelReady={status?.local_model.state==='ready'} modelState={status?.local_model.state} metrics={thisJob?.metrics??{context_limit:status?.job.metrics?.context_limit}} pending={pending||company.pending} create={()=>void create()} activityButton={activityButton} activityOpen={activityOpen} company={company.id?{open:companyOpen,toggle:toggleCompany,product:(()=>{const path=company.progress?.preview_url||company.progress?.product_url;return path?.startsWith('/')&&!path.startsWith('//')?'/assets/projects/'+company.id+path:undefined})()}:undefined} toggleActivity={()=>{documents?.close();setCompanyOpen(false);setActivityOpen(v=>!v);setSessionsOpen(false)}} focused={focused} onFocus={onFocus} onModels={onModels} onSettings={onSettings} toggleSessions={toggleSessions}/>

 <div className="hermes-chat-body"><div className="ha-chat-main"><div className="ha-transcript-viewport"><div ref={viewport} className={'hermes-messages '+(empty?'is-empty':'')} onScroll={()=>{const el=viewport.current;if(el){follow.current=el.scrollHeight-el.scrollTop-el.clientHeight<90;setShowLatest(!follow.current)}}}><div className="ha-conversation" aria-live="polite">
 {empty&&!company.enabled&&<ChatWelcome onPick={value=>{draft(value);composer.current?.focus()}}/>}
 <Transcript messages={shownMessages}/>
 {optimistic&&!shownMessages.slice(optimisticAfter.current).some(m=>m.role==='user'&&contentText(m.content)===optimistic)&&<article className="hermes-message user"><div className="ha-message-content"><MessageBody text={optimistic} user/></div></article>}
 {thisJob?.live_text&&active&&contentText(messages.at(-1)?.content)!==thisJob.live_text&&<article className="hermes-message assistant is-streaming"><div className="ha-assistant-mark">✳</div><div className="ha-message-content"><MessageBody text={thisJob.live_text}/><span className="ha-stream-dot" aria-label="답변 작성 중"/></div></article>}
 </div></div>{showLatest&&<IconButton className="ha-scroll-latest" type="button" aria-label="최신 메시지로 이동" onClick={()=>{follow.current=true;setShowLatest(false);viewport.current?.scrollTo({top:viewport.current.scrollHeight,behavior:'smooth'})}}><ArrowDown size={17}/>최신 메시지</IconButton>}
</div>
 <div className="ha-composer-dock">
 {thisJob?.approval&&<div className="hermes-approval"><b>{thisJob.approval.kind==='question'?'헤르메스의 질문':'작업 실행 확인'}</b><details><summary>요청 내용 보기</summary><pre>{thisJob.approval.detail}</pre></details>{thisJob.approval.kind==='question'?<><Textarea aria-label="헤르메스 질문에 답변" value={answer} onChange={e=>setAnswer(e.target.value)}/><Button disabled={pending||!answer.trim()} onClick={()=>void respond(true)}>답변 보내기</Button></>:<div className="hermes-actions"><Button tone="primary" disabled={pending} onClick={()=>void respond(true)}>허용</Button><Button disabled={pending} onClick={()=>void respond(false)}>거절</Button></div>}</div>}
 {active&&!thisJob&&!status?.job.application?<div className="hermes-current-activity is-active"><span>다른 대화에서 작업 중입니다.</span><Button onClick={()=>void choose(status?.job.session_id??'')}>해당 대화로 이동</Button></div>:null}
 {auto&&['active','paused'].includes(auto.status)&&<div className="hermes-autonomy-state"><b>{auto.mode==='goal'?'목표 실행':'반복 실행'}</b><span>{auto.status==='paused'?'일시정지':'진행 중'} · {auto.mode==='goal'?String(auto.turns_used??0)+'/'+String(auto.max_turns??0)+'회':String(auto.ticks_fired??0)+'회 실행'}</span>{auto.status==='paused'&&!active&&<Button disabled={pending} onClick={()=>void resume()}>재개</Button>}<details><summary>판정 내용</summary><p>{auto.paused_reason||auto.last_stop_reason||auto.last_reason||'진행 중입니다.'}</p></details></div>}
 <ErrorMessage message={error||company.error||thisJob?.error||''}/>
 <ChatComposer thinking={thinking.value} setThinking={thinking.change} localThinking={thinking.local} readOnly={readOnly} setReadOnly={setReadOnly} attachments={attachments} uploading={uploading} upload={files=>void upload(files)} removeAttachment={path=>setAttachments(files=>files.filter(file=>file.path!==path))} composer={composer} text={text} draft={draft} send={()=>void send()} stop={()=>void stop()} active={active} pending={pending||company.pending} company={false} stopping={status?.job.state==='stopping'} mode={mode} setMode={setMode} companyAvailable={!!company.sources.length} onCompany={()=>{const target=company.sources[0].session_id;if(text&&!localStorage.getItem(draftKey(target)))localStorage.setItem(draftKey(target),text);void choose(target)}} turns={turns} setTurns={setTurns} interval={interval} setIntervalSeconds={setIntervalSeconds} times={times} setTimes={setTimes}/></div>
 </div>{documents?.current?<DocumentPanel/>:activityOpen?<><IconButton className="ha-panel-backdrop ha-activity-backdrop" aria-label="작업 내역 배경 닫기" tabIndex={-1} onClick={()=>setActivityOpen(false)}/><ActivityPanel messages={shownMessages} activityPanel={activityPanel} thisJob={thisJob} selected={selected} pending={pending} active={active} onClose={()=>setActivityOpen(false)} onRefresh={onRefresh} archive={()=>void archive()}/></>:companyOpen&&company.id&&<><IconButton className="ha-panel-backdrop ha-activity-backdrop" aria-label="사업 관리 배경 닫기" tabIndex={-1} onClick={()=>setCompanyOpen(false)}/><CompanyPanel panel={companyPanel} id={company.id} items={company.ventures} progress={company.progress} pending={pending||company.pending} readOnly={readOnly} decide={(id,approve)=>void (async()=>{try{
  if(active){setError('현재 작업을 마친 뒤 승인하세요.');return}
  const source=company.sources.find(v=>v.id===company.id);if(!source)return;
  const linked=await request<{session_id:string}>('projects/conversation',{id:source.id,action:'session'});
  const result=await company.decide(id,approve);if(!approve||!result)return;
  await choose(linked.session_id);await thinking.prepare();onStatus(await request<AgentStatus>(prefix+'chat',{session_id:linked.session_id,message:'소유자가 사업안 '+result.name+' ('+id+')의 로컬 제작을 승인했습니다. company_records로 승인된 초안과 기존 진행을 확인하고 필요한 역할·순서를 직접 정해 미완성 작업을 이어가세요. 외부 공개·지출은 별도 승인 대상입니다.',mode:'goal',max_turns:turns,read_only:readOnly}));
 }catch(e){setError(failure(e))}})()} onClose={()=>{setCompanyOpen(false);localStorage.setItem('hermes.company.open','false')}}/></>}</div></section></div>;
}
