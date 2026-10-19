import {useEffect,useRef,useState,type ReactNode} from 'react';
import {request} from '@platform/data/api';
import {Button} from '@platform/ui/Primitives';

type Tab={id:string;view:string;title:string;src:string;revision:string};
export function AppTabs({children,onModels}:{children:ReactNode;onModels:()=>void}){
 const [tabs,setTabs]=useState<Tab[]>([]),[selected,setSelected]=useState('chat'),[mounted,setMounted]=useState(false);
 const frame=useRef<HTMLIFrameElement>(null);
 useEffect(()=>{let live=true;const refresh=()=>void request<{items:Tab[]}>('projects/workspace-tabs',{},'GET').then(r=>{if(live)setTabs(previous=>JSON.stringify(previous)===JSON.stringify(r.items)?previous:r.items)}).catch(()=>{if(live)setTabs([])});refresh();window.addEventListener('focus',refresh);const timer=setInterval(refresh,10000);return()=>{live=false;clearInterval(timer);window.removeEventListener('focus',refresh)}},[]);
 const tab=tabs.find(t=>t.id===selected),source=tab?.src||tabs[0]?.src;
 const select=(view:string)=>frame.current?.contentWindow?.postMessage({type:'platform:workspace-select',view},location.origin);
 useEffect(()=>{if(tab){setMounted(true);select(tab.view)}else if(selected!=='chat')setSelected('chat')},[selected,tabs]);
 useEffect(()=>{const receive=(e:MessageEvent)=>{if(e.origin!==location.origin||e.source!==frame.current?.contentWindow)return;if(e.data?.type==='platform:model-settings')onModels();if(e.data?.type==='platform:workspace-ready'&&tab)select(tab.view);if(e.data?.type==='platform:workspace-view'){const target=tabs.find(t=>t.src===source&&t.view===e.data.view);if(target)setSelected(target.id)}};window.addEventListener('message',receive);return()=>window.removeEventListener('message',receive)},[tabs,tab,source,onModels]);
 return <div className="flex min-h-0 min-w-0 flex-1 flex-col">{!!tabs.length&&<nav aria-label="대화 작업 화면" className="flex shrink-0 gap-1 overflow-x-auto border-b border-slate-200 bg-white px-3 py-2"><Button variant="ghost" tone={selected==='chat'?'primary':'neutral'} aria-current={selected==='chat'?'page':undefined} onClick={()=>setSelected('chat')}>대화</Button>{tabs.map(t=><Button key={t.id} variant="ghost" className="shrink-0" tone={selected===t.id?'primary':'neutral'} aria-current={selected===t.id?'page':undefined} onClick={()=>{setMounted(true);setSelected(t.id)}}>{t.title}</Button>)}</nav>}
 <div className={selected==='chat'?'flex min-h-0 flex-1 flex-col':'hidden'}>{children}</div>
 {mounted&&source&&<iframe ref={frame} src={source} title="연결된 회사 운영 화면" className={selected==='chat'?'hidden':'min-h-0 w-full flex-1 border-0'} onLoad={()=>{if(tab)select(tab.view)}}/>}
 </div>;
}
