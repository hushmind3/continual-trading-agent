import {SettingsActivity} from './useAgentSettings';
import {agentSettingsSections as sections,agentPages,agentLocation,navigateAgent} from '../agent_navigation';
import {useEffect,useState} from 'react';
import {Button} from '@platform/ui/Primitives';
import {WorkspaceSettings} from './workspace/WorkspaceSettings';
import {ModelSettings} from './models/ModelSettings';
import {McpPage} from './mcp/McpPage';
import {Skills} from './skills/Skills';
import {SystemPrompt} from './prompt/SystemPrompt';
import {AgentPrompts} from './agent-prompts/AgentPrompts';
import {working,type AgentStatus} from '../types';
export function Settings({status,onStatus,onChat}:{status?:AgentStatus;onStatus:(s:AgentStatus)=>void;onChat:()=>void}){
 const [tab,setTab]=useState(()=>agentLocation().section);
 const select=(id:string)=>{sessionStorage.setItem('hermes.settings.tab',id);navigateAgent('settings',id)};
 useEffect(()=>{const changed=()=>setTab(agentLocation().section);window.addEventListener('hashchange',changed);return()=>window.removeEventListener('hashchange',changed)},[]);
 const [visited,setVisited]=useState(()=>new Set([tab]));
 useEffect(()=>{setVisited(previous=>previous.has(tab)?previous:new Set([...previous,tab]))},[tab]);
 const current=sections.find(s=>s.id===tab)??sections[0];
 return <section className="hermes-settings-page"><header className="ha-settings-heading"><nav aria-label="헤르메스 설정 화면" className="hermes-tabs ha-settings-tabs">{agentPages.map(page=><Button key={page.id} aria-pressed={page.id===tab} onClick={()=>page.id==='chat'?onChat():select(page.id)}>{page.name}</Button>)}</nav></header><div className="ha-settings-layout"><div className="ha-settings-content" data-section={tab}><div className="ha-settings-section-title"><h2>{current.name}</h2><p>{current.description}</p></div>{sections.filter(section=>visited.has(section.id)||section.id===tab).map(section=><div key={section.id} hidden={section.id!==tab}><SettingsActivity.Provider value={section.id===tab}>{section.id==='workspace'&&<WorkspaceSettings busy={working(status)}/>} {section.id==='prompt'&&<SystemPrompt busy={working(status)}/>} {section.id==='agent-prompts'&&<AgentPrompts busy={working(status)}/>} {section.id==='models'&&<ModelSettings busy={working(status)} localModel={status?.local_model} onStatus={onStatus} onChat={onChat}/>} {section.id==='mcp'&&<McpPage busy={working(status)} onModels={()=>select('models')}/>} {section.id==='skills'&&<Skills busy={working(status)}/>}</SettingsActivity.Provider></div>)}</div></div></section>;
}
