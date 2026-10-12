import type {ComponentType,LazyExoticComponent} from 'react';
import type {LucideIcon} from 'lucide-react';
import type {Snapshot} from '../../data/types';
import type {BackendAction,BackendModuleMenu} from '../../data/menu_types';
export interface MenuItem {hash:string;name:string;group:string;icon:LucideIcon;component:LazyExoticComponent<ComponentType>;required:(keyof Snapshot)[];module?:boolean}
export function actionMenus(actions:BackendAction[],groupId:string,group:string,component:MenuItem['component'],icon:LucideIcon):MenuItem[]{
 return actions.filter(action=>action.group===groupId&&!['stock_data','stock_train','stock_backtest','native_call'].includes(action.id)).map<MenuItem>(action=>({hash:'feature-'+action.id,name:action.name,group,icon,component,required:['job']}));
}
export function moduleMenus(modules:BackendModuleMenu[],groupId:string,group:string,component:MenuItem['component'],icon:LucideIcon):MenuItem[]{
 return modules.filter(item=>item.group===groupId).map<MenuItem>(item=>({hash:'module-'+encodeURIComponent(item.id),name:(item.framework==='FinRL-X'?'FinRL-Trading':item.framework==='Python'?item.package:item.framework)+' · '+item.name,group,icon,component,required:['job'],module:true}));
}
