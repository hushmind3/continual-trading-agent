import {useEffect,useRef,useState} from 'react';
import {Bot,MessageSquare,Settings2,Plug,BookOpen,RefreshCw} from 'lucide-react';
import {request} from '../../../data/api';
import {Button,ErrorMessage} from '../../../ui/Primitives';
import {Chat} from './chat/Chat';
import {ModelSettings} from './models/ModelSettings';
import {McpSettings} from './mcp/McpSettings';
import {Skills} from './skills/Skills';
import {prefix,failure,working,type AgentStatus} from './types';
import './Hermes.css';

const tabs=[{id:'chat',name:'대화',icon:MessageSquare},{id:'models',name:'모델',icon:Settings2},{id:'mcp',name:'외부 도구',icon:Plug},{id:'skills',name:'스킬',icon:BookOpen}] as const;
export function Hermes(){
 const [tab,setTab]=useState<string>('chat'),[status,setStatus]=useState<AgentStatus>(),[error,setError]=useState('');
 const [retry,setRetry]=useState(0),last=useRef('');
 const polling=working(status)||status?.local_model.state==='loading';
 useEffect(()=>{let disposed=false,inFlight=false;let timer:ReturnType<typeof setTimeout>;const poll=async()=>{
  clearTimeout(timer);if(inFlight||disposed)return;inFlight=true;
  try{const next=await request<AgentStatus>(prefix+'status',{},'GET');if(!disposed){const key=JSON.stringify(next);if(key!==last.current){last.current=key;setStatus(next)}setError('');if(working(next)||next.local_model.state==='loading')timer=setTimeout(()=>void poll(),document.hidden?10000:1200)}}catch(e){if(!disposed){setError(failure(e));if(polling)timer=setTimeout(()=>void poll(),10000)}}finally{inFlight=false}
 };const resume=()=>{if(!document.hidden)void poll()};void poll();window.addEventListener('focus',resume);document.addEventListener('visibilitychange',resume);return()=>{disposed=true;clearTimeout(timer);window.removeEventListener('focus',resume);document.removeEventListener('visibilitychange',resume)}},[retry,polling]);
 return <div className="hermes-workspace"><header className="hermes-intro"><span className="hermes-brand"><Bot size={22}/></span><div><h2>내 컴퓨터에서, 함께 작업하기</h2><p>모델을 선택하고 대화로 작업을 맡기세요.</p></div><span className={'hermes-state '+(working(status)?'active':'')}>{working(status)?'작업 중':status?.local_model.state==='ready'?'로컬 모델 준비됨':'작업 대기'}</span><Button aria-label="작업 상태 새로고침" title="작업 상태 새로고침" onClick={()=>setRetry(v=>v+1)}><RefreshCw size={15}/></Button></header>
 <nav className="hermes-tabs" aria-label="Hermes 기능">{tabs.map(({id,name,icon:Icon})=><Button key={id} aria-pressed={tab===id} onClick={()=>setTab(id)}><Icon size={16}/>{name}</Button>)}</nav>
 {error&&<div className="hermes-error"><ErrorMessage message={error}/><Button onClick={()=>setRetry(v=>v+1)}>다시 연결</Button></div>}
 {tab==='chat'&&<Chat status={status} onStatus={setStatus} onModels={()=>setTab('models')}/>}{tab==='models'&&<ModelSettings busy={working(status)} localModel={status?.local_model} onStatus={setStatus} onChat={()=>setTab('chat')}/>}{tab==='mcp'&&<McpSettings busy={working(status)}/>}{tab==='skills'&&<Skills/>}
 </div>;
}
