import {useEffect,useRef,useState} from 'react';
import {Bot,MessageSquare,Settings2,Plug,BookOpen} from 'lucide-react';
import {request} from '../../../data/api';
import {Button,ErrorMessage} from '../../../ui/Primitives';
import {Chat} from './chat/Chat';
import {ModelSettings} from './models/ModelSettings';
import {McpSettings} from './mcp/McpSettings';
import {Skills} from './skills/Skills';
import {prefix,failure,working,type AgentStatus} from './types';
import './Hermes.css';

const tabs=[{id:'chat',name:'채팅',icon:MessageSquare},{id:'models',name:'모델 설정',icon:Settings2},{id:'mcp',name:'MCP',icon:Plug},{id:'skills',name:'스킬',icon:BookOpen}] as const;
export function Hermes(){
 const [tab,setTab]=useState<string>('chat'),[status,setStatus]=useState<AgentStatus>(),[error,setError]=useState('');
 const [retry,setRetry]=useState(0),last=useRef('');
 useEffect(()=>{let disposed=false;let timer:ReturnType<typeof setTimeout>;const poll=async()=>{
  try{const next=await request<AgentStatus>(prefix+'status',{},'GET');if(!disposed){const key=JSON.stringify(next);if(key!==last.current){last.current=key;setStatus(next)}setError('')}}catch(e){if(!disposed)setError(failure(e))}
  if(!disposed)timer=setTimeout(()=>void poll(),1500);
 };void poll();return()=>{disposed=true;clearTimeout(timer)}},[retry]);
 return <div className="hermes-workspace"><header className="hermes-intro"><span className="hermes-brand"><Bot size={23}/></span><div><h2>Hermes</h2><p>대화로 지시하고, 작업 과정을 확인하세요.</p></div><span className={'hermes-state '+(working(status)?'active':'')}>{working(status)?'작업 중':'대기'}</span></header>
 <nav className="hermes-tabs" aria-label="Hermes 기능">{tabs.map(({id,name,icon:Icon})=><Button key={id} aria-pressed={tab===id} onClick={()=>setTab(id)}><Icon size={16}/>{name}</Button>)}</nav>
 {error&&<div className="hermes-error"><ErrorMessage message={error}/><Button onClick={()=>setRetry(v=>v+1)}>다시 연결</Button></div>}
 {tab==='chat'&&<Chat status={status} onStatus={setStatus}/>}{tab==='models'&&<ModelSettings busy={working(status)} localModel={status?.local_model} onStatus={setStatus}/>}{tab==='mcp'&&<McpSettings busy={working(status)}/>}{tab==='skills'&&<Skills/>}
 </div>;
}
