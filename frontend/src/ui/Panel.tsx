import {Button} from './Primitives';
import {createContext,useContext,useId,useState,type ReactNode} from 'react';
import {ChevronDown,Info} from 'lucide-react';
export const CollapsiblePanels=createContext(false);
export function Panel({title,description,actions,children,className='',collapsible,defaultCollapsed=false}:{title:string;description?:string;actions?:ReactNode;children:ReactNode;className?:string;collapsible?:boolean;defaultCollapsed?:boolean}) {
 const enabled=useContext(CollapsiblePanels),fold=collapsible??enabled,[closed,setClosed]=useState(defaultCollapsed),id=useId();
 return <section className={'ui-panel min-w-0 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200/60 sm:p-6 '+className}>
  <header className="mb-5 flex flex-wrap items-start justify-between gap-4"><div className="ui-panel-title min-w-0">{fold?<Button type="button" aria-expanded={!closed} aria-controls={id} onClick={()=>setClosed(!closed)} className="!p-0 flex items-center gap-2 text-left"><ChevronDown size={15} className={'shrink-0 transition-transform '+(closed?'-rotate-90':'')}/><h2 className="text-base font-bold">{title}</h2></Button>:<h2 className="text-base font-bold">{title}</h2>}{description&&(!fold||!closed)&&<details className="ui-panel-help"><summary aria-label={title+' 안내'} title="안내"><Info size={15}/></summary><div className="ui-panel-help-copy">{description}</div></details>}</div>{actions}</header>{fold?<div id={id} hidden={closed}>{children}</div>:children}
 </section>;
}
export function KeyValues({items}:{items:[string,ReactNode][]}) {
  return <dl className="grid gap-x-6 sm:grid-cols-2">{items.map(([key,value])=><div className="min-w-0 border-b border-slate-100 py-3" key={key}><dt className="text-xs text-slate-400">{key}</dt><dd className="mt-1 break-words text-sm font-medium">{value??'미측정'}</dd></div>)}</dl>;
}
