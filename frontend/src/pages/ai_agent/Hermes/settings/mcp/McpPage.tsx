import {useState} from 'react';
import {Plug,Download} from 'lucide-react';
import {Button} from '../../../../../ui/Primitives';
import {McpSettings} from './McpSettings';
import {McpCatalog} from './McpCatalog';
export function McpPage({busy,onModels}:{busy:boolean;onModels:()=>void}){const [view,setView]=useState('catalog');return <><div className="hermes-subtabs"><Button aria-pressed={view==='catalog'} onClick={()=>setView('catalog')}><Download size={15}/>설치 카탈로그</Button><Button aria-pressed={view==='connections'} onClick={()=>setView('connections')}><Plug size={15}/>내 연결</Button></div>{view==='catalog'?<McpCatalog busy={busy} onConnections={()=>setView('connections')}/>:<McpSettings busy={busy} onModels={onModels}/>}</>}