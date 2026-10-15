import {useState} from 'react';
import {Settings2,Plug,BookOpen,ArrowLeft} from 'lucide-react';
import {Button} from '../../../../ui/Primitives';
import {ModelSettings} from './models/ModelSettings';
import {McpPage} from './mcp/McpPage';
import {Skills} from './skills/Skills';
import {working,type AgentStatus} from '../types';
export function Settings({status,onStatus,onChat}:{status?:AgentStatus;onStatus:(s:AgentStatus)=>void;onChat:()=>void}){
 const [tab,setTab]=useState('models');
 return <section className="hermes-settings-page"><header><Button onClick={onChat}><ArrowLeft size={16}/>대화로 돌아가기</Button><h3>설정</h3></header><nav aria-label="헤르메스 설정">{[{id:'models',name:'모델',icon:Settings2},{id:'mcp',name:'MCP',icon:Plug},{id:'skills',name:'스킬',icon:BookOpen}].map(({id,name,icon:Icon})=><Button key={id} aria-pressed={tab===id} onClick={()=>setTab(id)}><Icon size={16}/>{name}</Button>)}</nav>{tab==='models'&&<ModelSettings busy={working(status)} localModel={status?.local_model} onStatus={onStatus} onChat={onChat}/>} {tab==='mcp'&&<McpPage busy={working(status)} onModels={()=>setTab('models')}/>} {tab==='skills'&&<Skills busy={working(status)}/>}</section>;
}
