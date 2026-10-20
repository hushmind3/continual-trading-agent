import {useEffect,useRef,useState,type ReactNode} from 'react';
import {request} from '@platform/data/api';
import {Button} from '@platform/ui/Primitives';
import {AppExecution} from '@platform/ui/AppExecution';
import {renderToStaticMarkup} from 'react-dom/server';
import {MarkdownContent} from '@platform/ui/MarkdownContent';
import {CompanyConversations} from './CompanyConversation';
import {MeetingRoom} from './MeetingRoom';

type Tab={id:string;view:string;title:string;src:string;revision:string;conversation?:boolean;session_id:string};
export function AppTabs({children,onModels,modelName,modelState}:{children:ReactNode;onModels:()=>void;modelName:string;modelState?:string}){
 const [tabs,setTabs]=useState<Tab[]>([]),[selected,setSelected]=useState('chat'),[mounted,setMounted]=useState(false);
 const frame=useRef<HTMLIFrameElement>(null),markdown=useRef(new Map<string,string>());
 useEffect(()=>{let live=true;const refresh=()=>void request<{items:Tab[]}>('projects/workspace-tabs',{},'GET').then(r=>{if(live)setTabs(previous=>JSON.stringify(previous)===JSON.stringify(r.items)?previous:r.items)}).catch(()=>{if(live)setTabs([])});refresh();window.addEventListener('focus',refresh);const timer=setInterval(refresh,10000);return()=>{live=false;clearInterval(timer);window.removeEventListener('focus',refresh)}},[]);
 const tab=tabs.find(t=>t.id===selected),source=tab?.src||tabs[0]?.src;
 const shareEngine=()=>frame.current?.contentWindow?.postMessage({type:'hermes-engine-state',modelName,modelState},location.origin);
 useEffect(()=>{shareEngine()},[modelName,modelState,selected]);
 const companies=tabs.filter(t=>t.conversation&&t.view==='talk').map(t=>({id:t.id.split(':')[0],session_id:t.session_id,title:'AI 총괄 · '+t.title.replace('AI 총괄 대화','회사 운영')}));
 const shownTabs=tabs.filter(t=>!(t.conversation&&t.view==='talk'));
 const select=(view:string)=>frame.current?.contentWindow?.postMessage({type:'platform:workspace-select',view},location.origin);
 useEffect(()=>{if(tab){setMounted(true);select(tab.view)}else if(selected!=='chat'&&selected!=='meetings')setSelected('chat')},[selected,tabs]);
 useEffect(()=>{const receive=(e:MessageEvent)=>{if(e.origin!==location.origin||e.source!==frame.current?.contentWindow)return;if(e.data?.type==='platform:markdown'&&typeof e.data.text==='string'&&e.data.text.length<=30000&&typeof e.data.id==='string'){frame.current?.contentWindow?.postMessage({type:'platform:markdown-result',id:e.data.id,html:(()=>{let html=markdown.current.get(e.data.text);if(!html){html=renderToStaticMarkup(<MarkdownContent text={e.data.text}/>);if(markdown.current.size>=64)markdown.current.delete(markdown.current.keys().next().value!);markdown.current.set(e.data.text,html)}return html})()},location.origin)}if(e.data?.type==='platform:model-settings')onModels();if(e.data?.type==='platform:workspace-ready'&&tab)select(tab.view);if(e.data?.type==='platform:workspace-view'){const target=tabs.find(t=>t.src===source&&t.view===e.data.view);if(target){if(target.conversation&&target.view==='talk'){setSelected('chat');window.dispatchEvent(new CustomEvent('hermes:company-conversation',{detail:target.id.split(':')[0]}))}else setSelected(target.id)}}};window.addEventListener('message',receive);return()=>window.removeEventListener('message',receive)},[tabs,tab,source,onModels]);
 return <div className="flex min-h-0 min-w-0 flex-1 flex-col">{!!tabs.length&&<div className="flex min-w-0 shrink-0 items-center border-b border-slate-200 bg-white"><nav aria-label="대화 작업 화면" className="flex min-w-0 flex-1 gap-1 overflow-x-auto px-3 py-2"><Button variant="ghost" tone={selected==='chat'?'primary':'neutral'} aria-current={selected==='chat'?'page':undefined} onClick={()=>setSelected('chat')}>대화</Button>{shownTabs.map(t=><Button key={t.id} variant="ghost" className="shrink-0" tone={selected===t.id?'primary':'neutral'} aria-current={selected===t.id?'page':undefined} onClick={()=>{setMounted(true);setSelected(t.id)}}>{t.title}</Button>)}{!!companies.length&&<Button variant="ghost" tone={selected==='meetings'?'primary':'neutral'} aria-current={selected==='meetings'?'page':undefined} onClick={()=>setSelected('meetings')}>회의</Button>}</nav>{selected!=='chat'&&selected!=='meetings'&&<AppExecution projectId={(tab||tabs[0]).id.split(':')[0]}/>}</div>}
 <div className={selected==='chat'?'flex min-h-0 flex-1 flex-col':'hidden'}><CompanyConversations.Provider value={companies}>{children}</CompanyConversations.Provider></div>
 {selected==='meetings'&&<MeetingRoom companies={companies}/>}
 {mounted&&source&&<iframe ref={frame} src={source} title="연결된 회사 운영 화면" className={selected==='chat'||selected==='meetings'?'hidden':'min-h-0 w-full flex-1 border-0'} onLoad={()=>{if(tab)select(tab.view);shareEngine()}}/>}
 </div>;
}
