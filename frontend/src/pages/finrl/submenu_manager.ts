import {lazy} from 'react';
import {GraduationCap,Workflow} from 'lucide-react';
import {actionMenus,type MenuItem} from '../../shell/menu_groups/menu_types';
import type {BackendAction} from '../../data/menu_types';
const feature=lazy(()=>import('../management/backend_browser/FeatureWorkspace').then(m=>({default:m.FeatureWorkspace})));
export const menus:MenuItem[]=[
 {hash:'learning',name:'정책 학습',group:'FinRL · 메인',icon:GraduationCap,component:lazy(()=>import('./policy_learning/TrainingWorkspace').then(m=>({default:m.TrainingWorkspace}))),required:['settings','model','data','experts','job','checkpoints','resources']},
 {hash:'frameworks',name:'FinRL 모듈 · 도구',group:'FinRL · 메인',icon:Workflow,component:lazy(()=>import('./tools/FinrlToolsWorkspace').then(m=>({default:m.FinrlToolsWorkspace}))),required:['job']},
];
export function registeredMenus(actions:BackendAction[]){return [...menus,...actionMenus(actions,'finrl','FinRL · 메인',feature,Workflow)];}
