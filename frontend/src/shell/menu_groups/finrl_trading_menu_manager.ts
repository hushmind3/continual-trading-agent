import {lazy} from 'react';
import {Workflow} from 'lucide-react';
import {actionMenus,moduleMenus,type MenuItem} from './menu_types';
import type {BackendAction,BackendModuleMenu} from '../../data/menu_types';
const feature=lazy(()=>import('../../pages/frameworks/FeatureWorkspace').then(m=>({default:m.FeatureWorkspace})));
export const menus:MenuItem[]=[
 {hash:'finrl-trading',name:'보조 데이터 · 전략 · 도구',group:'FinRL-Trading · 보조',icon:Workflow,component:lazy(()=>import('../../pages/frameworks/FrameworkWorkspace').then(m=>({default:m.FinrlTradingWorkspace}))),required:['job']},
];
export function registeredMenus(actions:BackendAction[],modules:BackendModuleMenu[]=[]){return [...menus,...actionMenus(actions,'finrl_trading','FinRL-Trading · 보조',feature,Workflow),...moduleMenus(modules,'finrl_trading','FinRL-Trading · 보조',moduleScreen,Workflow)];}

const moduleScreen=lazy(()=>import('../../pages/frameworks/FrameworkWorkspace').then(m=>({default:m.ModuleWorkspace})));
