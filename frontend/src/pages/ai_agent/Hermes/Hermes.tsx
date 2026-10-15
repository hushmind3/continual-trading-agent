import {useEffect,useRef,useState} from 'react';
import {Bot,MessageSquare,Settings2,RefreshCw} from 'lucide-react';
import {request} from '../../../data/api';
import {Button,ErrorMessage} from '../../../ui/Primitives';
import {Chat} from './chat/Chat';
import {Settings} from './settings/Settings';
import {prefix,failure,working,type AgentStatus} from './types';
import './Hermes.css';
import './Workspace.css';

const tabs=[{id:'chat',name:'대화',icon:MessageSquare},{id:'settings',name:'설정',icon:Settings2}] as const;
export function Hermes(){
 const [tab,setTab]=useState<string>('chat'),[status,setStatus]=useState<AgentStatus>(),[error,setError]=useState('');
 const [retry,setRetry]=useState(0),last=useRef('');
 const polling=working(status)||status?.local_model.state==='loading';
 useEffect(()=>{let disposed=false,inFlight=false;let timer:ReturnType<typeof setTimeout>;const poll=async()=>{
  clearTimeout(timer);if(inFlight||disposed)return;inFlight=true;
  try{const next=await request<AgentStatus>(prefix+'status',{},'GET');if(!disposed){const key=JSON.stringify(next);if(key!==last.current){last.current=key;setStatus(next)}setError('');if(working(next)||next.local_model.state==='loading')timer=setTimeout(()=>void poll(),document.hidden?10000:1200)}}catch(e){if(!disposed){setError(failure(e));if(polling)timer=setTimeout(()=>void poll(),10000)}}finally{inFlight=false}
 };const resume=()=>{if(!document.hidden)void poll()};void poll();window.addEventListener('focus',resume);document.addEventListener('visibilitychange',resume);return()=>{disposed=true;clearTimeout(timer);window.removeEventListener('focus',resume);document.removeEventListener('visibilitychange',resume)}},[retry,polling]);
 return <div className={'hermes-workspace '+(tab==='chat'?'is-chat':'is-settings')}><header className="hermes-toolbar"><span className="hermes-brand"><Bot size={19}/></span><h2>헤르메스</h2><nav aria-label="Hermes 기능">{tabs.map(({id,name,icon:Icon})=><Button key={id} aria-pressed={tab===id} onClick={()=>setTab(id)}><Icon size={16}/>{name}</Button>)}</nav><span className={'hermes-state '+(working(status)?'active':'')}>{working(status)?'작업 중':status?.local_model.state==='ready'?'모델 준비됨':'작업 대기'}</span><Button aria-label="작업 상태 새로고침" title="작업 상태 새로고침" onClick={()=>setRetry(v=>v+1)}><RefreshCw size={15}/></Button></header>
 {error&&<div className="hermes-error"><ErrorMessage message={error}/><Button onClick={()=>setRetry(v=>v+1)}>다시 연결</Button></div>}
 <div className="hermes-chat-mount" hidden={tab!=='chat'}><Chat status={status} onStatus={setStatus} onModels={()=>setTab('settings')}/></div>{tab==='settings'&&<Settings status={status} onStatus={setStatus} onChat={()=>setTab('chat')}/>}
 </div>;
}
