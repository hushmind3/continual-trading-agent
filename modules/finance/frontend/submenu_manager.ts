import {lazy} from 'react';
import {Workflow} from 'lucide-react';
import {menus as trading} from './trading/submenu_manager';
import {menus as finrl} from './finrl/submenu_manager';
import {menus as extensions} from './extensions/submenu_manager';
import {menus as management} from './management/submenu_manager';
import {actionMenus,type MenuItem} from '@platform/shell/menu_groups/menu_types';
import type {BackendAction} from '@platform/data/menu_types';
const feature=lazy(()=>import('./management/all_backend_features/AllBackendFeatures').then(m=>({default:m.AllBackendFeatures})));
export const menus:MenuItem[]=[...trading,...finrl,...extensions,...management].map(menu=>({...menu,group:'금융'}));
export function registeredMenus(actions:BackendAction[]){return [...menus,...actionMenus(actions,'finance','금융',feature,Workflow)];}
