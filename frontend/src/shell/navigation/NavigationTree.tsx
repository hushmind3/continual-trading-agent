import {useState} from 'react';
import {ChevronDown} from 'lucide-react';
import type {MenuItem} from '../menu_groups/menu_types';
import {MenuLink} from './MenuLink';
interface Props {items:MenuItem[];active:string;compact?:boolean;onNavigate:()=>void;errorCount:(group:string)=>number}
export function NavigationTree({items,active,compact=false,onNavigate,errorCount}:Props){
 const [closed,setClosed]=useState(new Set<string>());
 const toggle=(id:string)=>setClosed(old=>{const next=new Set(old);if(next.has(id))next.delete(id);else next.add(id);return next});
 items=items.filter(item=>item.sidebar!==false);
 return <>{[...new Set(items.map(item=>item.group))].map(group=>{
  const members=items.filter(item=>item.group===group),sections=[...new Map(members.filter(item=>item.section).map(item=>[item.section!.id,item.section!])).values()];
  return <details key={group} open={compact||!closed.has(group)} className="workspace-menu-group">
   <summary className={compact?'sr-only':''} onClick={event=>{event.preventDefault();toggle(group)}}>{group}{errorCount(group)>0&&<span className="workspace-menu-error">{errorCount(group)}</span>}</summary>
   <nav aria-label={group}>
    {members.filter(item=>!item.section).map(item=><MenuLink key={item.hash} item={item} active={active} compact={compact} onNavigate={onNavigate}/>)}
    {sections.map(section=>{const key=group+'/'+section.id,Icon=section.icon;return <details key={key} open={compact||!closed.has(key)} className="workspace-menu-section">
     <summary className={compact?'sr-only':''} onClick={event=>{event.preventDefault();toggle(key)}}><Icon size={17}/><span>{section.name}</span><ChevronDown size={14}/></summary>
     <div>{members.filter(item=>item.section?.id===section.id).map(item=><MenuLink key={item.hash} item={item} active={active} compact={compact} leaf onNavigate={onNavigate}/>)}</div>
    </details>})}
   </nav>
  </details>;
 })}</>;
}
