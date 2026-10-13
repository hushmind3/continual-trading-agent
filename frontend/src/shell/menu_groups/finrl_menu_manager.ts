import {lazy} from 'react';
import {GraduationCap,Workflow} from 'lucide-react';
import {actionMenus,type MenuItem} from './menu_types';
import type {BackendAction} from '../../data/menu_types';
const feature=lazy(()=>import('../../pages/frameworks/FeatureWorkspace').then(m=>({default:m.FeatureWorkspace})));
export const menus:MenuItem[]=[
 {hash:'learning',name:'정책 학습',group:'FinRL · 메인',icon:GraduationCap,component:lazy(()=>import('../../pages/training/TrainingWorkspace').then(m=>({default:m.TrainingWorkspace}))),required:['settings','model','data','experts','job','checkpoints','resources']},
 {hash:'frameworks',name:'FinRL 모듈 · 도구',group:'FinRL · 메인',icon:Workflow,component:lazy(()=>import('../../pages/frameworks/FrameworkWorkspace').then(m=>({default:m.FinrlToolsWorkspace}))),required:['job']},
];
export function registeredMenus(actions:BackendAction[]){return [...menus,...actionMenus(actions,'finrl','FinRL · 메인',feature,Workflow)];}
