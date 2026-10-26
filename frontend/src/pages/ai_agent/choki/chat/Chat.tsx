import {DocumentWorkspace,DocumentPanel,useDocumentWorkspace} from '@platform/ui/DocumentPreview';
import {useEffect,useLayoutEffect,useRef,useState} from 'react';
import {ArrowDown} from 'lucide-react';
import {request} from '@platform/data/api';
import {Button,IconButton,Textarea,ErrorMessage} from '@platform/ui/Primitives';
import {prefix,failure,working,contentText,type AgentStatus,type Message,type Session,type SessionDetail,type AutonomousState,type Metrics} from '../types';
import {Transcript,CurrentActivity} from './ChatStream';
import {MessageBody} from './MessageBody';
import {ChatHeader} from './ChatHeader';
import {SessionSidebar} from './SessionSidebar';
import {ActivityPanel} from './ActivityPanel';
import {ChatComposer,type Attachment} from './ChatComposer';
import {ChatWelcome} from './ChatWelcome';
import {useThinking} from './useThinking';
import {executeCommand} from './nativeCommands';
import {openOfficial} from '../agent_navigation';
import {AppTabs} from './AppTabs';
import {CompanyPanel} from './CompanyPanel';
import {companySession,useCompanyConversation} from './CompanyConversation';

interface Props {status?:AgentStatus;modelName:string;focused:boolean;onFocus:()=>void;onStatus:(s:AgentStatus)=>void;onModels:()=>void;onSettings:()=>void;onRefresh:()=>void}
const draftKey=(id:string)=>'hermes.draft.'+(id||'new');
const mobile=()=>window.matchMedia('(max-width:760px)').matches;
const connectionState=(status?:Props['status'])=>status?.model_connection?.state||status?.local_model.state;
export function Chat(props:Props){return <AppTabs status={props.status} onModels={props.onModels} modelName={props.modelName} modelState={connectionState(props.status)}><DocumentWorkspace><ChatWorkspace {...props}/></DocumentWorkspace></AppTabs>;}
function ChatWorkspace({status,modelName,focused,onFocus,onStatus,onModels,onSettings,onRefresh}:Props){
 const documents=useDocumentWorkspace();
 const thinking=useThinking(modelName);
 const [readOnly,updateReadOnly]=useState(()=>localStorage.getItem('hermes.read-mode')==='true');
 const setReadOnly=(value:boolean)=>{updateReadOnly(value);try{localStorage.setItem('hermes.read-mode',String(value))}catch{/* The switch also works without storage. */}};
 const [commandOutput,setCommandOutput]=useState<{command:string;text:string}>();
 const [attachments,setAttachments]=useState<Attachment[]>([]),[uploading,setUploading]=useState(false);
 const upload=async(files:File[])=>{if(uploading)return;if(files.length+attachments.length>8){setError('첨부 파일은 최대 8개입니다.');return}setUploading(true);setError('');try{for(const file of files){if(file.size>8*1024*1024)throw new Error(file.name+': 파일당 최대 8 MiB입니다.');const content=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]??'');reader.onerror=()=>reject(new Error('파일을 읽지 못했습니다.'));reader.readAsDataURL(file)});const saved=await request<Attachment>(prefix+'artifact/upload',{name:file.name,content});setAttachments(previous=>[...previous,saved])}}catch(error){setError(failure(error))}finally{setUploading(false)}};
 const [sessions,setSessions]=useState<Session[]>([]),[selected,setSelected]=useState(''),[messages,setMessages]=useState<Message[]>([]),[text,setText]=useState(()=>localStorage.getItem(draftKey(''))||''),[error,setError]=useState(''),[pending,setPending]=useState(false),[optimistic,setOptimistic]=useState('');
 const initialDraft=useRef<{edited:boolean;text:string}>({edited:false,text:''});
 const [sessionsOpen,setSessionsOpen]=useState(false),[activityOpen,setActivityOpen]=useState(false),[query,setQuery]=useState(''),[showLatest,setShowLatest]=useState(false);
 const [targetError,setTargetError]=useState(false);
 const [switching,setSwitching]=useState(false),switchVersion=useRef(0),sessionRead=useRef(0);
 const [companyOpen,setCompanyOpen]=useState(false);
 const companyPanel=useRef<HTMLElement>(null);
 const viewport=useRef<HTMLDivElement>(null),follow=useRef(true),selection=useRef(''),optimisticAfter=useRef(0),composer=useRef<HTMLTextAreaElement>(null);
 const sessionPanel=useRef<HTMLElement>(null),activityPanel=useRef<HTMLElement>(null),sessionButton=useRef<HTMLButtonElement>(null),activityButton=useRef<HTMLButtonElement>(null);
 const [answer,setAnswer]=useState(''),[mode,setMode]=useState('chat'),[turns,setTurns]=useState(20),[interval,setIntervalSeconds]=useState(60),[times,setTimes]=useState(5),[savedAutonomy,setSavedAutonomy]=useState<AutonomousState>();
 const sessionRecords=useRef<Session[]>([]);
 const [savedMetrics,setSavedMetrics]=useState<Metrics>();
 const company=useCompanyConversation(selected,sessions);
 const active=working(status),thisJob=status?.job.session_id===selected?status.job:undefined,auto=thisJob?.autonomy??savedAutonomy;
 const shownMessages=messages;
 const toggleCompany=()=>{setCompanyOpen(value=>{localStorage.setItem('hermes.company.open',String(!value));return !value});setActivityOpen(false);setSessionsOpen(false);documents?.close()};
 useEffect(()=>{const media=window.matchMedia('(max-width:760px)');const change=()=>{if(media.matches)setCompanyOpen(false)};media.addEventListener('change',change);return()=>media.removeEventListener('change',change)},[]);
 const toggleSessions=()=>setSessionsOpen(value=>{if(!value){setActivityOpen(false);setCompanyOpen(false);documents?.close()}return !value});
 const draft=(value:string)=>{initialDraft.current={edited:!selection.current,text:value};setText(value);try{localStorage.setItem(draftKey(selected),value)}catch{/* Keep typing if local storage is full. */}};
 const list=async()=>{const rows=await request<Session[]>(prefix+'sessions',{},'GET');const all=[...rows.filter(r=>!company.sources.some(v=>v.session_id===r.id)),...company.sources.map(v=>({id:v.session_id,title:v.title,managed:true}))];sessionRecords.current=all;setSessions(all);return all};
 const choose=async(id:string,initial=false)=>{
  const version=++switchVersion.current;++sessionRead.current;setSwitching(true);setTargetError(false);try{
  const linked=company.sources.find(v=>v.session_id===id||companySession(v.id)===id||v.id===sessionRecords.current.find(row=>row.id===id)?.company_id);
  if(linked&&id===companySession(linked.id)){const remembered=sessionStorage.getItem('hermes.company-session.'+linked.id);if(sessionRecords.current.some(row=>row.id===remembered&&row.company_id===linked.id))id=remembered!}
  if(linked&&(id===linked.session_id||id===companySession(linked.id))){try{id=(await request<{session_id:string}>('projects/conversation',{id:linked.id,action:'session'})).session_id}catch(e){setTargetError(true);setError(failure(e));return}}
  if(version!==switchVersion.current)return;
  if(linked)sessionStorage.setItem('hermes.company-session.'+linked.id,id);
  else sessionStorage.setItem('hermes.regular-session',id);
  const retained=initial&&initialDraft.current.edited?initialDraft.current.text:undefined;
  if(retained!==undefined){try{localStorage.setItem(draftKey(id),retained);localStorage.removeItem(draftKey(''))}catch{/* Keep the typed draft even if storage is unavailable. */}initialDraft.current.edited=false}
  if(!initial)setAttachments([]);follow.current=true;setShowLatest(false);sessionStorage.setItem('hermes.session',id);selection.current=id;setSelected(id);setSavedMetrics(undefined);setText(retained??localStorage.getItem(draftKey(id))??'');setOptimistic('');setMessages([]);setSavedAutonomy(undefined);setError('');setSessionsOpen(false);
  if(!id)return;
  const read=++sessionRead.current;try{const data=await request<SessionDetail>(prefix+'session',{id},'GET');if(selection.current===id&&read===sessionRead.current){setMessages(data.messages);setSavedMetrics(data.metrics);const a=await request<{goal?:Record<string,unknown>;loop?:Record<string,unknown>}>(prefix+'autonomy',{id},'GET');if(selection.current===id){const [kind,state]=a.loop?.status==='active'?['loop',a.loop]:a.goal?.status==='active'?['goal',a.goal]:a.loop?.status==='paused'?['loop',a.loop]:['goal',a.goal];setSavedAutonomy(state?{...state,mode:kind} as AutonomousState:undefined)}}}catch(e){if(selection.current===id)setError(failure(e))}
  }finally{if(version===switchVersion.current)setSwitching(false)}
 };
 useEffect(()=>{if(documents?.current){setSessionsOpen(false);setActivityOpen(false);setCompanyOpen(false)}},[documents?.current]);
 useEffect(()=>{let disposed=false;void list().then(rows=>{if(!disposed&&rows.length&&!selection.current){void choose(rows.find(r=>r.id===sessionStorage.getItem('hermes.session'))?.id??rows[0].id,true)}}).catch(e=>{if(!disposed)setError(failure(e))});return()=>{disposed=true}},[company.sources.map(v=>v.id).join(',')]);
 useEffect(()=>{const resume=(event:Event)=>{const id=(event as CustomEvent<{id:string}>).detail?.id;if(id)void choose(id)};window.addEventListener('hermes:resume-session',resume);return()=>window.removeEventListener('hermes:resume-session',resume)},[company.sources.map(v=>v.id).join(',')]);
 useEffect(()=>{const receive=(event:Event)=>{const id=(event as CustomEvent<string>).detail;const current=selection.current;const same=sessionRecords.current.find(row=>row.id===current)?.company_id===id||company.sources.some(source=>source.id===id&&source.session_id===current);void choose(same?current:companySession(id))};window.addEventListener('hermes:company-conversation',receive);return()=>window.removeEventListener('hermes:company-conversation',receive)},[company.sources.map(v=>v.id).join(',')]);
 useEffect(()=>{if(!status?.job.session_id)return;if(['complete','failed','stopped','paused'].includes(status.job.state)){void list().catch(e=>setError(failure(e)));if(selection.current===status.job.session_id){const read=++sessionRead.current;void request<SessionDetail>(prefix+'session',{id:selection.current},'GET').then(row=>{if(selection.current===row.session.id&&read===sessionRead.current){setMessages(row.messages);setSavedMetrics(row.metrics);setOptimistic('')}}).catch(e=>setError(failure(e)))}}},[status?.job.state,status?.job.session_id]);
 useLayoutEffect(()=>{if(follow.current&&viewport.current)viewport.current.scrollTop=viewport.current.scrollHeight},[messages,status?.job.live_text,optimistic]);
 useEffect(()=>{if(!active||!selected||status?.job.session_id!==selected)return;let live=true;const poll=()=>{const read=++sessionRead.current;void request<SessionDetail>(prefix+'session',{id:selected},'GET').then(row=>{if(live&&read===sessionRead.current&&selection.current===row.session.id)setMessages(prev=>JSON.stringify(prev)===JSON.stringify(row.messages)?prev:row.messages)}).catch(()=>{})};poll();const timer=setInterval(poll,2500);return()=>{live=false;clearInterval(timer)}},[active,selected,status?.job.session_id]);
 useEffect(()=>{
  const panel=activityOpen?activityPanel.current:sessionsOpen?sessionPanel.current:companyOpen?companyPanel.current:null,origin=document.activeElement as HTMLElement|null;
  if(panel&&(mobile()||sessionsOpen))panel.querySelector<HTMLElement>('button,input')?.focus();
  const keys=(e:KeyboardEvent)=>{
   if(e.key==='Escape'){if(activityOpen){setActivityOpen(false);activityButton.current?.focus()}else if(sessionsOpen){setSessionsOpen(false);sessionButton.current?.focus()}else if(companyOpen){setCompanyOpen(false);document.querySelector<HTMLButtonElement>('[aria-label="사업 관리 보기"]')?.focus()}}
   if(e.key==='Tab'&&panel&&(mobile()||sessionsOpen)){const focusable=[...panel.querySelectorAll<HTMLElement>('button:not(:disabled),input,select,textarea,summary,a[href]')];const first=focusable[0],last=focusable.at(-1);if(!first||!last)return;if(e.shiftKey&&(document.activeElement===first||!panel.contains(document.activeElement))){e.preventDefault();last.focus()}else if(!e.shiftKey&&(document.activeElement===last||!panel.contains(document.activeElement))){e.preventDefault();first.focus()}}
  };
  window.addEventListener('keydown',keys);return()=>{window.removeEventListener('keydown',keys);if(panel&&(mobile()||sessionsOpen))origin?.focus()};
 },[sessionsOpen,activityOpen,companyOpen]);
 const create=async()=>{setPending(true);setError('');try{const row=await request<SessionDetail>(prefix+'session/create',company.enabled?{company_id:company.id}:{});await list();await choose(row.session.id);composer.current?.focus()}catch(e){setError(failure(e))}finally{setPending(false)}};
 const send=async(override?:string,targetSession=selected)=>{if(targetError)return;if((!(override??text).trim()&&!attachments.length)||pending||switching||company.pending||uploading)return;const prompt=((override??text).trim()||'첨부 파일을 확인해 주세요.')+(attachments.length?'\n\n첨부 파일:\n'+attachments.map(file=>'['+file.name+']('+file.path.replaceAll('\\','/')+')').join('\n'):'');++sessionRead.current;setPending(true);setError('');follow.current=true;setShowLatest(false);try{if(active){if(!thisJob)throw new Error('작업 중인 대화로 이동해 메시지를 보내세요.');const next=await request<AgentStatus>(prefix+'chat/steer',{session_id:selected,message:prompt,attachments:attachments.map(file=>file.path)});optimisticAfter.current=messages.length;setOptimistic(prompt);setText('');setAttachments([]);localStorage.removeItem(draftKey(selected));onStatus(next);return}await thinking.prepare();const next=await request<AgentStatus>(prefix+'chat',{session_id:targetSession||undefined,message:prompt,attachments:attachments.map(file=>file.path),read_only:readOnly,mode,max_turns:turns,times,interval_seconds:interval||null});localStorage.removeItem(draftKey(selected));optimisticAfter.current=next.job.session_id===selected?messages.length:0;if(next.job.session_id!==selected)setMessages([]);selection.current=next.job.session_id??'';sessionStorage.setItem('hermes.session',selection.current);if(!company.enabled)sessionStorage.setItem('hermes.regular-session',selection.current);setSelected(selection.current);setOptimistic(prompt);setText('');setAttachments([]);onStatus(next);await list()}catch(e){setError(failure(e))}finally{setPending(false)}};
 const runCommand=async(command:string)=>{
  if(pending||switching||company.pending)return;
  const [name,...parts]=command.split(/\s+/),arg=parts.join(' ');
  if(name==='/commands')command='/help'+(arg?' '+arg:'');
  if(!arg&&['/new','/clear'].includes(name)){void create();return}
  if(!arg&&['/sessions','/resume'].includes(name)){setSessionsOpen(true);return}
  if(!arg&&name==='/model'){onModels();return}
  if(!arg&&name==='/palette'){draft('/');composer.current?.focus();return}
  if(!arg&&name==='/plugins'){openOfficial('/plugins');return}
  if(!arg&&name==='/profile'){openOfficial('/profiles');return}
  if(!arg&&name==='/redraw'){onRefresh();return}
  if(name==='/copy'){
   try{await navigator.clipboard.writeText(contentText(messages.filter(row=>row.role==='assistant').at(-1)?.content));setCommandOutput({command,text:'마지막 답변을 복사했습니다.'});draft('')}catch(error){setError(failure(error))}return;
  }
  if(name==='/stop'&&active){void stop();return}
  if(name==='/status'&&active){setActivityOpen(true);onRefresh();return}
  if(['/approve','/deny'].includes(name)&&thisJob?.approval){void respond(name==='/approve');return}
  if(name==='/steer'&&active&&arg){void send(arg);return}
  if(!arg&&['/goal','/loop'].includes(name)){setMode(name.slice(1));return}
  if(active){setError('현재 작업을 마친 뒤 이 명령을 실행하세요. 실행 중지와 추가 지시는 작업 중에도 사용할 수 있습니다.');return}
  setPending(true);setError('');setCommandOutput(undefined);
  try{
   const result=await executeCommand(selected,command);
   if(result.type==='select'&&result.session_id){await choose(result.session_id)}
   else if(result.type==='send'||result.type==='skill'){
    setPending(false);await send(result.message||'',result.session_id||selected);
   }else if(result.type==='prefill'){draft(result.display||result.message||'')}
   else if(result.download){
    const file=result.download,url=URL.createObjectURL(new Blob([file.content],{type:file.format==='html'?'text/html;charset=utf-8':file.format==='json'?'application/json':'text/markdown;charset=utf-8'}));
    const link=document.createElement('a');link.href=url;link.download=file.filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    setCommandOutput({command,text:result.output||'대화 파일을 내려받습니다.'});
   }
   else{setCommandOutput({command,text:[result.output,result.warning].filter(Boolean).join('\n\n')||'명령을 처리했습니다.'});follow.current=true;setShowLatest(false)}
   if(!selected&&result.session_id&&!['send','skill','select'].includes(result.type||''))await choose(result.session_id);
   if(selected&&!['send','skill','select'].includes(result.type||'')){
    const fresh=await request<SessionDetail>(prefix+'session',{id:selected},'GET');
    if(selection.current===selected){setMessages(fresh.messages);setSavedMetrics(fresh.metrics)}
   }
   window.dispatchEvent(new Event('hermes:model-changed'));onRefresh();await list();
  }catch(error){setError(failure(error))}finally{setPending(false)}
 };
 const stop=async()=>{setPending(true);try{onStatus(await request<AgentStatus>(prefix+'stop',{}))}catch(e){setError(failure(e))}finally{setPending(false)}};
 const archive=async()=>{if(!selected)return;setPending(true);try{await request(prefix+'session/archive',{id:selected});selection.current='';sessionStorage.removeItem('hermes.session');setSelected('');setMessages([]);setText(localStorage.getItem(draftKey(''))||'');setSavedAutonomy(undefined);setOptimistic('');await list()}catch(e){setError(failure(e))}finally{setPending(false)}};
 const resume=async()=>{if(!auto)return;setPending(true);setError('');try{await thinking.prepare();onStatus(await request<AgentStatus>(prefix+'chat',{session_id:selected,message:auto.goal??auto.prompt,mode:auto.mode,resume:true,read_only:readOnly}))}catch(e){setError(failure(e))}finally{setPending(false)}};
 const respond=async(allow:boolean)=>{setPending(true);setError('');try{await request(prefix+'answer',{allow,text:answer});setAnswer('')}catch(e){setError(failure(e))}finally{setPending(false)}};
 useEffect(()=>{const show=()=>{setCompanyOpen(true);setActivityOpen(false);setSessionsOpen(false);documents?.close()};window.addEventListener('hermes:review-proposals',show);return()=>window.removeEventListener('hermes:review-proposals',show)},[documents?.close]);
 const title=sessions.find(r=>r.id===selected)?.title||'새 대화',shownModel=modelName||sessions.find(r=>r.id===selected)?.model;
 const visible=sessions.filter(r=>(r.title||'제목 없는 대화').toLowerCase().includes(query.toLowerCase()));
 const empty=!shownMessages.length&&!optimistic&&!(thisJob?.live_text&&active);
 return <div className={'hermes-chat-layout '+(sessionsOpen?'sessions-open':'sessions-closed')}>
 {sessionsOpen&&<><IconButton className="ha-panel-backdrop ha-session-backdrop" aria-label="대화 목록 배경 닫기" tabIndex={-1} onClick={()=>setSessionsOpen(false)}/><SessionSidebar sessionPanel={sessionPanel} toggleSessions={toggleSessions} create={()=>void create()} pending={pending} query={query} setQuery={setQuery} visible={visible} selected={selected} choose={id=>void choose(id)} archive={()=>void archive()} archiveDisabled={company.root||active&&!!thisJob} rename={async(id,title)=>{await request(prefix+'session/rename',{id,title});await list()}}/></>}
 <section className="hermes-chat"><ChatHeader companyTitle={company.enabled?company.sources.find(source=>source.id===company.id)?.title:undefined} sessionsOpen={sessionsOpen} sessionButton={sessionButton} title={title} shownModel={shownModel} modelReady={connectionState(status)==='ready'} modelState={connectionState(status)} metrics={thisJob?.metrics?.api_calls?{...thisJob.metrics,cumulative_input_tokens:savedMetrics?.cumulative_input_tokens}:savedMetrics??thisJob?.metrics??{context_limit:status?.job.metrics?.context_limit}} pending={pending||switching||company.pending} create={()=>void create()} activityButton={activityButton} activityOpen={activityOpen} company={company.id?{open:companyOpen,toggle:toggleCompany}:undefined} toggleActivity={()=>{documents?.close();setCompanyOpen(false);setActivityOpen(v=>!v);setSessionsOpen(false)}} focused={focused} onFocus={onFocus} onModels={onModels} onSettings={onSettings} toggleSessions={toggleSessions}/>

 <div className="hermes-chat-body"><div className="ha-chat-main"><div className="ha-transcript-viewport"><div ref={viewport} className={'hermes-messages '+(empty?'is-empty':'')} onScroll={()=>{const el=viewport.current;if(el){follow.current=el.scrollHeight-el.scrollTop-el.clientHeight<90;setShowLatest(!follow.current)}}}><div className="ha-conversation" aria-live="polite">
 {empty&&!company.enabled&&<ChatWelcome onPick={value=>{draft(value);composer.current?.focus()}}/>}
 <Transcript messages={shownMessages}/>

 {optimistic&&!shownMessages.slice(optimisticAfter.current).some(m=>m.role==='user'&&contentText(m.content).includes(optimistic))&&<article className="hermes-message user"><div className="ha-message-content"><MessageBody text={optimistic} user/></div></article>}
 {thisJob?.live_text&&active&&contentText(messages.filter(message=>message.role==='assistant').at(-1)?.content)!==thisJob.live_text&&<article className="hermes-message assistant is-streaming"><div className="ha-assistant-mark">✳</div><div className="ha-message-content"><MessageBody text={thisJob.live_text}/><span className="ha-stream-dot" aria-label="답변 작성 중"/></div></article>}
 {commandOutput&&<article className="hermes-message assistant" data-command-result><div className="flex items-center justify-between"><b>{commandOutput.command}</b><IconButton aria-label="명령 결과 닫기" onClick={()=>setCommandOutput(undefined)}>×</IconButton></div><pre className="max-h-96 overflow-auto">{commandOutput.text}</pre></article>}
 </div></div>{showLatest&&<IconButton className="ha-scroll-latest" type="button" aria-label="최신 메시지로 이동" onClick={()=>{follow.current=true;setShowLatest(false);viewport.current?.scrollTo({top:viewport.current.scrollHeight,behavior:'smooth'})}}><ArrowDown size={17}/>최신 메시지</IconButton>}
</div>
 <div className="ha-composer-dock">
 {thisJob?.approval&&<div className="hermes-approval"><b>{thisJob.approval.kind==='question'?'choki의 질문':'작업 실행 확인'}</b><details><summary>요청 내용 보기</summary><pre>{thisJob.approval.detail}</pre></details>{thisJob.approval.kind==='question'?<><Textarea aria-label="choki 질문에 답변" value={answer} onChange={e=>setAnswer(e.target.value)}/><Button disabled={pending||!answer.trim()} onClick={()=>void respond(true)}>답변 보내기</Button></>:<div className="hermes-actions"><Button tone="primary" disabled={pending} onClick={()=>void respond(true)}>허용</Button><Button disabled={pending} onClick={()=>void respond(false)}>거절</Button></div>}</div>}
 {active&&!thisJob&&!status?.job.application?<div className="hermes-current-activity is-active"><span>다른 대화에서 작업 중입니다.</span><Button onClick={()=>void choose(status?.job.session_id??'')}>해당 대화로 이동</Button></div>:null}
 {auto&&['active','paused'].includes(auto.status)&&<div className="hermes-autonomy-state"><b>{auto.mode==='goal'?'목표 실행':'반복 실행'}</b><span>{auto.status==='paused'?'일시정지':'진행 중'} · {auto.mode==='goal'?String(auto.turns_used??0)+'/'+String(auto.max_turns??0)+'회':String(auto.ticks_fired??0)+'회 실행'}</span>{auto.status==='paused'&&!active&&<Button disabled={pending} onClick={()=>void resume()}>재개</Button>}<details><summary>판정 내용</summary><p>{auto.paused_reason||auto.last_stop_reason||auto.last_reason||'진행 중입니다.'}</p></details></div>}
 <ErrorMessage message={error||company.error||thisJob?.error||thisJob?.metrics_error||''}/>
 <CurrentActivity job={thisJob} active={active&&!!thisJob}/>
 <ChatComposer onCommand={command=>void runCommand(command)} onModels={onModels} create={()=>void create()} onActivity={()=>setActivityOpen(value=>!value)} onBusiness={company.enabled?toggleCompany:undefined} blocked={targetError} canSteer={thisJob?.can_steer??false} reasoning={thinking.reasoning} thinking={thinking.value} setThinking={thinking.change} localThinking={thinking.local} readOnly={readOnly} setReadOnly={setReadOnly} attachments={attachments} uploading={uploading} upload={files=>void upload(files)} removeAttachment={path=>setAttachments(files=>files.filter(file=>file.path!==path))} composer={composer} text={text} draft={draft} send={()=>void send()} stop={()=>void stop()} active={active} pending={pending||switching||company.pending} company={company.enabled} conversationId={selected} companySources={company.choices} onConversation={id=>{const regular=sessionStorage.getItem('hermes.regular-session');void choose(id||(sessions.some(row=>row.id===regular&&!row.managed)?regular:'')||'')}} stopping={status?.job.state==='stopping'} mode={mode} setMode={setMode} turns={turns} setTurns={setTurns} interval={interval} setIntervalSeconds={setIntervalSeconds} times={times} setTimes={setTimes}/></div>
 </div>{documents?.current?<DocumentPanel/>:activityOpen?<><IconButton className="ha-panel-backdrop ha-activity-backdrop" aria-label="작업 내역 배경 닫기" tabIndex={-1} onClick={()=>setActivityOpen(false)}/><ActivityPanel messages={shownMessages} activityPanel={activityPanel} thisJob={thisJob} selected={selected} pending={pending} active={active} onClose={()=>setActivityOpen(false)} onRefresh={onRefresh} archive={()=>void archive()}/></>:companyOpen&&company.id&&<><IconButton className="ha-panel-backdrop ha-activity-backdrop" aria-label="사업 관리 배경 닫기" tabIndex={-1} onClick={()=>setCompanyOpen(false)}/><CompanyPanel panel={companyPanel} id={company.id} items={company.ventures} progress={company.progress} pending={pending||switching||company.pending} readOnly={readOnly} decide={(id,approve)=>void (async()=>{try{
  if(active){setError('현재 작업을 마친 뒤 승인하세요.');return}
  const source=company.sources.find(v=>v.id===company.id);if(!source)return;
  const linked=company.enabled?{session_id:selected}:await request<{session_id:string}>('projects/conversation',{id:source.id,action:'session'});
  const result=await company.decide(id,approve);if(!approve||!result)return;
  await choose(linked.session_id);await thinking.prepare();setMode('loop');setTimes(0);onStatus(await request<AgentStatus>(prefix+'chat',{session_id:linked.session_id,workspace:result.workspace,message:'대표가 사업안 '+result.name+' ('+id+')의 승인 범위 내 자율 제작·운영을 승인했습니다. company_records overview로 승인안·진행 상태·직원별 전문성을 확인하세요. 필요한 작업을 스스로 찾아 begin으로 배정하고, delegate_task의 staff_id에 해당 직원 고유 ID를 지정해 실제 도구와 현재 작업 공간으로 위임하세요. 실제 산출물 경로·실패 원인·검증 결과를 다음 직원에게 전달하고 finish/fail로 기록하세요. 이 반복의 각 주기에는 현재 가장 필요한 작업을 진행하고 결과에 따라 다음 일을 선택하세요. 제품이 준비되면 승인된 출시·고객 확보·운영·실제 매출과 비용 개선을 이어가세요. 외부 공개·계정 인증·결제·지출은 별도 승인이 필요하며 연결되지 않은 항목을 성공으로 보고하지 마세요. 막히면 필요한 결정·연결만 요청하고 같은 실패를 반복하지 마세요. 새 사업은 새 승인 대상입니다.',mode:'loop',times:0,interval_seconds:interval||null,read_only:readOnly}));
 }catch(e){setError(failure(e))}})()}/></>}</div></section></div>;
}
