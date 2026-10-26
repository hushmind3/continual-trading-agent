import {SettingsActivity} from './useAgentSettings';
import {agentSettingsSections as sections,agentPages,agentLocation,navigateAgent} from '../agent_navigation';
import {lazy,Suspense,useEffect,useState} from 'react';
import {Button} from '@platform/ui/Primitives';
import {WorkspaceSettings} from './workspace/WorkspaceSettings';
import {SystemPrompt} from './prompt/SystemPrompt';
import {AgentPrompts} from './agent-prompts/AgentPrompts';
import {ModelSettings} from './models/ModelSettings';
import {working,type AgentStatus} from '../types';
const OfficialWorkspace=lazy(()=>import('./official/OfficialWorkspace').then(module=>({default:module.OfficialWorkspace})));
export function Settings({status,onChat}:{status?:AgentStatus;onStatus:(s:AgentStatus)=>void;onChat:()=>void}){
 const [tab,setTab]=useState(()=>agentLocation().section);
 const select=(id:string)=>{sessionStorage.setItem('hermes.settings.tab',id);navigateAgent('settings',id)};
 useEffect(()=>{const changed=()=>setTab(agentLocation().section);window.addEventListener('hashchange',changed);return()=>window.removeEventListener('hashchange',changed)},[]);
 const [visited,setVisited]=useState(()=>new Set([tab]));
 useEffect(()=>{setVisited(previous=>previous.has(tab)?previous:new Set([...previous,tab]))},[tab]);
 const nativePage=tab==='mcp'?'/mcp':tab==='skills'?'/skills':undefined;
 const nativeActive=Boolean(nativePage)||tab==='official';
 const current=sections.find(s=>s.id===tab)??sections[0];
 return <section className="hermes-settings-page"><header className="ha-settings-heading"><nav aria-label="헤르메스 설정 화면" className="hermes-tabs ha-settings-tabs">{agentPages.map(page=><Button key={page.id} aria-pressed={page.id===tab} onClick={()=>page.id==='chat'?onChat():select(page.id)}>{page.name}</Button>)}</nav></header><div className="ha-settings-layout"><div className="ha-settings-content" data-section={tab}>{tab==='models'&&<ModelSettings/>}{!nativeActive&&tab!=='models'&&<div className="ha-settings-section-title"><h2>{current.name}</h2><p>{current.description}</p></div>}<div hidden={!nativeActive}>{[...visited].some(id=>['models','mcp','skills','official'].includes(id))&&<Suspense fallback={<p role="status">기능을 불러오고 있습니다.</p>}><OfficialWorkspace page={nativePage}/></Suspense>}</div>{sections.filter(section=>['workspace','prompt','agent-prompts'].includes(section.id)&&(visited.has(section.id)||section.id===tab)).map(section=><div key={section.id} hidden={section.id!==tab}><SettingsActivity.Provider value={section.id===tab}>{section.id==='workspace'&&<WorkspaceSettings busy={working(status)}/>} {section.id==='prompt'&&<SystemPrompt busy={working(status)}/>} {section.id==='agent-prompts'&&<AgentPrompts busy={working(status)}/>}</SettingsActivity.Provider></div>)}</div></div></section>;
}
