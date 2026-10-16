import {agentSettingsSections as sections,agentPages,agentLocation,navigateAgent} from '../../agent_navigation';
import {useEffect,useState} from 'react';
import {ArrowLeft} from 'lucide-react';
import {Button,Select} from '../../../../ui/Primitives';
import {ModelSettings} from './models/ModelSettings';
import {McpPage} from './mcp/McpPage';
import {Skills} from './skills/Skills';
import {SystemPrompt} from './prompt/SystemPrompt';
import {working,type AgentStatus} from '../types';
export function Settings({status,onStatus,onChat}:{status?:AgentStatus;onStatus:(s:AgentStatus)=>void;onChat:()=>void}){
 const [tab,setTab]=useState(()=>agentLocation().section);
 const select=(id:string)=>{sessionStorage.setItem('hermes.settings.tab',id);navigateAgent('settings',id)};
 useEffect(()=>{const changed=()=>setTab(agentLocation().section);window.addEventListener('hashchange',changed);return()=>window.removeEventListener('hashchange',changed)},[]);
 const current=sections.find(s=>s.id===tab)??sections[0];
 return <section className="hermes-settings-page"><header className="ha-settings-heading"><Button onClick={onChat}><ArrowLeft size={17}/>대화로 돌아가기</Button><label className="ha-agent-page-switch"><span>AI 에이전트</span><Select aria-label="AI 에이전트 화면" value={tab} onChange={event=>event.target.value==='chat'?onChat():select(event.target.value)}>{agentPages.map(page=><option key={page.id} value={page.id}>{page.name}</option>)}</Select></label></header><div className="ha-settings-layout"><div className="ha-settings-content" data-section={tab}><div className="ha-settings-section-title"><h2>{current.name}</h2><p>{current.description}</p></div>{tab==='prompt'&&<SystemPrompt busy={working(status)}/>} {tab==='models'&&<ModelSettings busy={working(status)} localModel={status?.local_model} onStatus={onStatus} onChat={onChat}/>} {tab==='mcp'&&<McpPage busy={working(status)} onModels={()=>select('models')}/>} {tab==='skills'&&<Skills busy={working(status)}/>}</div></div></section>;
}
