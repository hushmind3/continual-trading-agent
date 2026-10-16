import type {MenuItem} from '../menu_groups/menu_types';
interface Props {item:MenuItem;active:string;compact:boolean;onNavigate:()=>void;leaf?:boolean}
export function MenuLink({item,active,compact,onNavigate,leaf=false}:Props){
 const Icon=item.icon;
 return <a href={'#'+item.hash} title={item.section?item.section.name+' · '+item.name:item.name} onClick={onNavigate} aria-current={active===item.hash?'page':undefined} className={'workspace-menu-item'+(leaf?' workspace-menu-leaf':'')}>
  {(!leaf||compact)&&<Icon size={18} className="shrink-0"/>}<span className={compact?'sr-only':''}>{item.name}</span>
 </a>;
}
