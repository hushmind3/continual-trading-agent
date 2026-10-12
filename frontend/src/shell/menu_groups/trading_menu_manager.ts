import type {BackendModuleMenu} from '../../data/menu_types';
import {lazy} from 'react';
import {Activity,Database,Landmark,Workflow} from 'lucide-react';
import {moduleMenus,type MenuItem} from './menu_types';
export const menus:MenuItem[]=[
 {hash:'markets',name:'시장 · 저장 데이터',group:'거래 운영',icon:Database,component:lazy(()=>import('../../pages/markets/MarketScanner').then(m=>({default:m.MarketScanner}))),required:['data']},
 {hash:'control',name:'운영 제어',group:'거래 운영',icon:Activity,component:lazy(()=>import('../../pages/operations/OperationsBoard').then(m=>({default:m.OperationsBoard}))),required:['operations','resources','job','capabilities']},
 {hash:'paper',name:'가상계좌 · 주문',group:'거래 운영',icon:Landmark,component:lazy(()=>import('../../pages/paper/PaperWorkspace').then(m=>({default:m.PaperWorkspace}))),required:['operations']},
];

const moduleScreen=lazy(()=>import('../../pages/frameworks/FrameworkWorkspace').then(m=>({default:m.ModuleWorkspace})));
export function registeredMenus(modules:BackendModuleMenu[]){return [...menus,...moduleMenus(modules,'trading','거래 운영',moduleScreen,Workflow)];}
