import type {ComponentType,LazyExoticComponent} from 'react';
import type {LucideIcon} from 'lucide-react';
import type {Snapshot} from '../../data/types';
import type {BackendAction} from '../../data/menu_types';
export interface MenuSection {id:string;name:string;icon:LucideIcon}
export interface MenuItem {hash:string;name:string;group:string;icon:LucideIcon;component:LazyExoticComponent<ComponentType>;required:(keyof Snapshot)[];mountKey?:string;section?:MenuSection;sidebar?:boolean}
export function actionMenus(actions:BackendAction[],groupId:string,group:string,component:MenuItem['component'],icon:LucideIcon):MenuItem[]{
 return actions.filter(action=>action.group===groupId&&action.id!=='native_call').map<MenuItem>(action=>({hash:action.menu_id+'/'+action.id,name:action.name,group,icon,component,required:['job']}));
}
