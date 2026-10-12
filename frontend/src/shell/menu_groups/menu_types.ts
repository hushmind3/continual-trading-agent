import type {ComponentType,LazyExoticComponent} from 'react';
import type {LucideIcon} from 'lucide-react';
import type {Snapshot} from '../../data/types';
import type {BackendAction} from '../../data/menu_types';
import type {SourceModule} from '../../data/menu_types';
export interface MenuItem {hash:string;name:string;group:string;icon:LucideIcon;component:LazyExoticComponent<ComponentType>;required:(keyof Snapshot)[]}
export function actionMenus(actions:BackendAction[],groupId:string,group:string,component:MenuItem['component'],icon:LucideIcon):MenuItem[]{
 return actions.filter(action=>action.group===groupId&&!['stock_data','stock_train','stock_backtest','native_call'].includes(action.id)).map<MenuItem>(action=>({hash:'feature-'+action.id,name:action.name,group,icon,component,required:['job']}));
}
export function moduleMenus(modules:SourceModule[],framework:string,group:string,component:MenuItem['component'],icon:LucideIcon):MenuItem[]{
 return modules.filter(module=>module.framework===framework).map<MenuItem>(module=>({hash:'source-module-'+encodeURIComponent(module.id),name:module.path.replace(/^[^/]+\//,''),group,icon,component,required:[]}));
}
