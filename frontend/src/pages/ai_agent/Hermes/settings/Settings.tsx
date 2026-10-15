import {useState} from 'react';
import {Settings2,Plug,BookOpen,ArrowLeft,ChevronRight} from 'lucide-react';
import {Button} from '../../../../ui/Primitives';
import {ModelSettings} from './models/ModelSettings';
import {McpPage} from './mcp/McpPage';
import {Skills} from './skills/Skills';
import {working,type AgentStatus} from '../types';
const sections=[{id:'models',name:'모델',description:'로컬 모델·서버·작업 도구',icon:Settings2},{id:'mcp',name:'MCP',description:'서버 설치와 연결 관리',icon:Plug},{id:'skills',name:'스킬',description:'작업 지침과 사용 설정',icon:BookOpen}];
export function Settings({status,onStatus,onChat}:{status?:AgentStatus;onStatus:(s:AgentStatus)=>void;onChat:()=>void}){
 const [tab,setTab]=useState(()=>sessionStorage.getItem('hermes.settings.tab')||'models');
 const select=(id:string)=>{setTab(id);sessionStorage.setItem('hermes.settings.tab',id)};
 const current=sections.find(s=>s.id===tab)??sections[0];
 return <section className="hermes-settings-page"><header className="ha-settings-heading"><Button onClick={onChat}><ArrowLeft size={17}/>대화로 돌아가기</Button><span>헤르메스 설정</span></header><div className="ha-settings-layout"><nav aria-label="헤르메스 설정"><p>환경 설정</p>{sections.map(({id,name,description,icon:Icon})=><Button type="button" key={id} aria-label={name} aria-current={tab===id?'page':undefined} onClick={()=>select(id)}><Icon size={18}/><span><b>{name}</b><small>{description}</small></span><ChevronRight size={14}/></Button>)}</nav><div className="ha-settings-content" data-section={tab}><div className="ha-settings-section-title"><h2>{current.name}</h2><p>{current.description}</p></div>{tab==='models'&&<ModelSettings busy={working(status)} localModel={status?.local_model} onStatus={onStatus} onChat={onChat}/>} {tab==='mcp'&&<McpPage busy={working(status)} onModels={()=>select('models')}/>} {tab==='skills'&&<Skills busy={working(status)}/>}</div></div></section>;
}
