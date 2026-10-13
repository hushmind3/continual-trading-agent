import {lazy} from 'react';
import {Boxes,Workflow} from 'lucide-react';
import {actionMenus,type MenuItem} from '../../../shell/menu_groups/menu_types';
import type {BackendAction} from '../../../data/menu_types';
const feature=lazy(()=>import('../management/all_backend_features/AllBackendFeatures').then(m=>({default:m.AllBackendFeatures})));
export const menus:MenuItem[]=[
 {hash:'finance/moe',name:'MoE',group:'프로젝트 확장',icon:Boxes,component:lazy(()=>import('./moe/Moe').then(m=>({default:m.Moe}))),required:['experts','job','library']},
];
export function registeredMenus(actions:BackendAction[]){return [...menus,...actionMenus(actions,'extensions','프로젝트 확장',feature,Workflow)];}
