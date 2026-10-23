import {useState} from 'react';
import {Tabs} from '@platform/ui/Primitives';
import {McpSettings} from './McpSettings';
import {McpCatalog} from './McpCatalog';
export function McpPage({busy,onModels}:{busy:boolean;onModels:()=>void}) {
 const [view,setView]=useState(()=>sessionStorage.getItem('hermes.mcp.view')==='connections'?'connections':'catalog');
 const [connectionsVisited,setConnectionsVisited]=useState(view==='connections');
 const select=(id:string)=>{setView(id);sessionStorage.setItem('hermes.mcp.view',id);if(id==='connections')setConnectionsVisited(true)};
 return <div className="agent-settings-stack"><Tabs items={[{id:'catalog',label:'설치 카탈로그'},{id:'connections',label:'내 연결'}]} value={view} onChange={select}/>
  <div hidden={view!=='catalog'}><McpCatalog busy={busy} onConnections={()=>select('connections')}/></div>
  {connectionsVisited&&<div hidden={view!=='connections'}><McpSettings busy={busy} onModels={onModels}/></div>}
 </div>;
}
